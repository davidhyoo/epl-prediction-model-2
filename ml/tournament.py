"""
tournament.py
=============
Deterministic 2026 World Cup tournament logic shared by the ingest step (which
produces the single *canonical* bracket + "actual" results) and the prediction
step (which runs a vectorised Monte-Carlo championship simulation).

Format: 48 teams, 12 groups of 4 -> 72 group matches. Top 2 of each group plus
the 8 best third-placed teams -> Round of 32 -> ... -> Final (104 matches).

The Round-of-32 seeding here is a *simplified, self-consistent* strength seeding
(seed 1 v 32, etc.) rather than FIFA's official pairing table — this is
documented in the README and Methodology page.
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np

from common import (
    Team, GROUPS, HOME_ADV, expected_goals, elo_win_prob, rng,
)


# --------------------------------------------------------------------------- #
# Group draw (pot-based snake draw with light confederation spreading)
# --------------------------------------------------------------------------- #
def draw_groups(teams: list[Team]) -> None:
    """Assign each team a group A..L in place. Hosts are seeded to fixed groups."""
    r = rng("draw")

    # Pots of 12. Hosts are forced into pot 1 (as real seeded teams); the rest of
    # pot 1 is the strongest non-hosts, then pots 2-4 by descending Elo.
    hosts = [t for t in teams if t.host]
    non_hosts = sorted((t for t in teams if not t.host), key=lambda t: -t.elo0)
    pot1 = hosts + non_hosts[: 12 - len(hosts)]
    rest = non_hosts[12 - len(hosts):]
    pots = [pot1, rest[:12], rest[12:24], rest[24:36]]
    for pi, pot in enumerate(pots, start=1):
        for t in pot:
            t.pot = pi

    groups: dict[str, list[Team]] = {g: [] for g in GROUPS}

    # Seed the three hosts as group heads (Mexico A, Canada B, USA D).
    host_slots = {"MEX": "A", "CAN": "B", "USA": "D"}
    placed = set()
    for code, g in host_slots.items():
        t = next(x for x in teams if x.code == code)
        groups[g].append(t)
        placed.add(code)

    # Remaining pot-1 teams fill the other group heads.
    pot1_rest = [t for t in pot1 if t.code not in placed]
    open_groups = [g for g in GROUPS if not groups[g]]
    for t, g in zip(sorted(pot1_rest, key=lambda x: -x.elo0), open_groups):
        groups[g].append(t)
        placed.add(t.code)

    def confed_ok(group_teams: list[Team], cand: Team) -> bool:
        same = sum(1 for x in group_teams if x.confederation == cand.confederation)
        limit = 2 if cand.confederation == "UEFA" else 1
        return same < limit

    # Pots 2..4 via snake order with best-effort confederation spreading.
    for pot_i in (2, 3, 4):
        pot = [t for t in teams if t.pot == pot_i and t.code not in placed]
        r.shuffle(pot)
        order = GROUPS if pot_i % 2 == 0 else list(reversed(GROUPS))
        for g in order:
            # pick first candidate satisfying confederation rule, else first.
            choice = next((c for c in pot if confed_ok(groups[g], c)), pot[0])
            groups[g].append(choice)
            pot.remove(choice)
            placed.add(choice.code)

    for g, members in groups.items():
        for t in members:
            t.group = g


# --------------------------------------------------------------------------- #
# Match simulation (data-generating process uses latent strengths)
# --------------------------------------------------------------------------- #
def play_match(rating_a: float, rating_b: float, generator: np.random.Generator,
               knockout: bool = False) -> dict:
    """Simulate one match. Returns goals, winner ('A'/'B'/'D') and penalties."""
    lam_a, lam_b = expected_goals(rating_a, rating_b)
    ga = int(generator.poisson(lam_a))
    gb = int(generator.poisson(lam_b))
    pens = None
    if ga == gb and knockout:
        # extra-time nudge, then penalty shootout
        if generator.random() < 0.18:
            if generator.random() < elo_win_prob(rating_a, rating_b):
                ga += 1
            else:
                gb += 1
        if ga == gb:
            p = 0.5 + (elo_win_prob(rating_a, rating_b) - 0.5) * 0.35
            if generator.random() < p:
                pa, pb = 4, int(generator.integers(2, 4))
            else:
                pa, pb = int(generator.integers(2, 4)), 4
            pens = (pa, pb)
    if ga > gb:
        winner = "A"
    elif gb > ga:
        winner = "B"
    else:
        winner = "A" if (pens and pens[0] > pens[1]) else ("B" if pens else "D")
    return {"ga": ga, "gb": gb, "winner": winner, "pens": pens}


# --------------------------------------------------------------------------- #
# Standings & qualification
# --------------------------------------------------------------------------- #
def blank_record() -> dict:
    return {"played": 0, "won": 0, "drawn": 0, "lost": 0,
            "gf": 0, "ga": 0, "gd": 0, "points": 0}


def apply_result(rec: dict, gf: int, ga: int) -> None:
    rec["played"] += 1
    rec["gf"] += gf
    rec["ga"] += ga
    rec["gd"] = rec["gf"] - rec["ga"]
    if gf > ga:
        rec["won"] += 1
        rec["points"] += 3
    elif gf == ga:
        rec["drawn"] += 1
        rec["points"] += 1
    else:
        rec["lost"] += 1


def rank_key(rec: dict, elo0: float):
    return (rec["points"], rec["gd"], rec["gf"], elo0)


def group_tables(records: dict[str, dict], teams_by_code: dict[str, Team]
                 ) -> dict[str, list[str]]:
    """Return ordered list of team codes per group (best first)."""
    tables: dict[str, list[str]] = {}
    for g in GROUPS:
        members = [c for c, t in teams_by_code.items() if t.group == g]
        members.sort(key=lambda c: rank_key(records[c], teams_by_code[c].elo0),
                     reverse=True)
        for rank, c in enumerate(members, start=1):
            records[c]["groupRank"] = rank
        tables[g] = members
    return tables


def qualified_ranked(tables: dict[str, list[str]], records: dict[str, dict],
                     teams_by_code: dict[str, Team]) -> list[str]:
    """Top-2 per group + 8 best third-placed teams, returned ranked (seed order)."""
    winners = [tables[g][0] for g in GROUPS]
    runners = [tables[g][1] for g in GROUPS]
    thirds = [tables[g][2] for g in GROUPS]
    thirds.sort(key=lambda c: rank_key(records[c], teams_by_code[c].elo0),
                reverse=True)
    best_thirds = thirds[:8]

    def tier_sort(codes: list[str]) -> list[str]:
        return sorted(codes,
                      key=lambda c: rank_key(records[c], teams_by_code[c].elo0),
                      reverse=True)

    # Seeds: all group winners (best->worst), then runners-up, then best thirds.
    ranked = tier_sort(winners) + tier_sort(runners) + tier_sort(best_thirds)
    return ranked  # length 32, index 0 == seed 1


def seed_order(n: int) -> list[int]:
    """Standard single-elimination seeding order (1-indexed) for n = 2^k."""
    order = [1]
    while len(order) < n:
        m = len(order) * 2
        nxt: list[int] = []
        for x in order:
            nxt.append(x)
            nxt.append(m + 1 - x)
        order = nxt
    return order


def r32_bracket_positions(ranked32: list[str]) -> list[str]:
    """Map ranked seeds into bracket positions (length 32)."""
    order = seed_order(32)
    return [ranked32[s - 1] for s in order]


# --------------------------------------------------------------------------- #
# Vectorised Monte-Carlo championship simulation
# --------------------------------------------------------------------------- #
KNOCKOUT_STAGES = ["round-of-16", "quarter-final", "semi-final", "final", "champion"]


def simulate_knockouts(bracket_positions_idx: np.ndarray, eff: np.ndarray,
                       n_sims: int, generator: np.random.Generator) -> dict:
    """
    Vectorised knockout Monte-Carlo.

    bracket_positions_idx : int array (32,) of global team indices in bracket order
    eff                   : float array (n_teams,) effective ratings
    Returns dict of milestone -> count array over all teams (len n_teams).
    """
    n_teams = eff.shape[0]
    counts = {stage: np.zeros(n_teams, dtype=np.int64) for stage in KNOCKOUT_STAGES}
    counts["round-of-32"] = np.zeros(n_teams, dtype=np.int64)

    # arr: (n_sims, current_round_size) of team indices
    arr = np.tile(bracket_positions_idx.reshape(1, -1), (n_sims, 1))
    # everyone reaches R32
    np.add.at(counts["round-of-32"], bracket_positions_idx, n_sims)

    stage_names = ["round-of-16", "quarter-final", "semi-final", "final", "champion"]
    while arr.shape[1] > 1:
        a = arr[:, 0::2]
        b = arr[:, 1::2]
        ra = eff[a]
        rb = eff[b]
        prob_a = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
        u = generator.random(a.shape)
        winners = np.where(u < prob_a, a, b)
        arr = winners
        stage = stage_names.pop(0)
        # count winners as having reached the next milestone
        flat = winners.reshape(-1)
        np.add.at(counts[stage], flat, 1)

    return counts


def build_eff_ratings(teams: list[Team], elo_by_code: dict[str, float],
                      squad_by_code: dict[str, float]) -> tuple[np.ndarray, dict]:
    """Effective ratings for the championship sim: current Elo blended with a
    squad-strength bonus and a host advantage. Returns (array, code->index)."""
    idx = {t.code: i for i, t in enumerate(teams)}
    eff = np.zeros(len(teams))
    for t in teams:
        base = elo_by_code.get(t.code, t.elo0)
        squad_bonus = (squad_by_code.get(t.code, 50.0) - 50.0) * 1.6
        host_bonus = HOME_ADV * 0.55 if t.host else 0.0
        eff[idx[t.code]] = base + squad_bonus + host_bonus
    return eff, idx
