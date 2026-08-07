"""
ucl_bracket.py  —  Champions-League knockout model (championship odds)
=====================================================================
The domestic ``club_simulate`` answers "who finishes top of a round-robin?".
A cup is a different beast: the trophy is decided by a single-elimination tree
of two-legged ties (plus a one-off neutral final), so who you *happen to draw*
matters as much as how good you are.

This module:

  1. **Reconstructs the actual bracket tree** from the knockout matches that were
     played — grouping the two legs of each tie, resolving the real winner
     (aggregate score, then the penalty shoot-out the source records), and
     wiring each tie to the child ties whose winners fed it. Byes (the eight
     league-phase seeds that skip the play-off round) enter the tree as fixed
     leaves. Nothing about the *draw* is invented — we use the pairings that
     genuinely happened.

  2. **Monte-Carlos the championship** over that fixed tree: every tie is
     re-played from an Elo/Poisson score model (home advantage cancels over two
     legs; the final is neutral), winners propagate upward, and we count how
     often each club lifts the trophy.

  3. Produces a **convergence timeline** — championship probability at "bracket
     set", then after each knockout round — by fixing the ties already decided
     to their real winners and simulating only what remained. This is the cup
     analogue of the league title race: the forecast starts spread across the
     contenders and sharpens onto the eventual winner round by round.

Everything is deterministic (fixed seed) and offline.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from club_simulate import _expected_goals
from leagues import HOME_ADV, LEAGUE_AVG_GOALS, SEED

N_SIMS = 8000
RACE_N_SIMS = 6000
GOALS_PER_100_ELO = 0.45
MAX_LAMBDA = 5.0

# knockout stages in bracket order (earliest → final)
_STAGE_ORDER = ["playoff", "r16", "qf", "sf", "final"]
_STAGE_LABEL = {
    "playoff": "Play-offs", "r16": "Round of 16", "qf": "Quarter-finals",
    "sf": "Semi-finals", "final": "Final",
}


# --------------------------------------------------------------------------- #
# Tie = one knockout matchup (one or two legs)
# --------------------------------------------------------------------------- #
class Tie:
    __slots__ = ("id", "stage", "teams", "winner", "neutral", "legs",
                 "slots")

    def __init__(self, tie_id: str, stage: str, teams: tuple[str, str],
                 winner: str | None, legs: list[tuple[str, str]]):
        self.id = tie_id
        self.stage = stage
        self.teams = teams
        self.winner = winner          # actual winner (None if undecided/unplayed)
        self.neutral = stage == "final"
        self.legs = legs              # [(home, away), ...] as actually staged
        # each slot is ("tie", child_tie) or ("team", code) — filled by the tree
        self.slots: list[tuple[str, object]] = []


def _tie_winner(matches: list[dict]) -> tuple[tuple[str, str], str | None,
                                              list[tuple[str, str]]]:
    """Aggregate a tie's legs → (teams, actual winner, leg home/away order)."""
    agg: dict[str, int] = defaultdict(int)
    pens: dict[str, int] = {}
    legs: list[tuple[str, str]] = []
    teams: list[str] = []
    for m in sorted(matches, key=lambda x: (x.get("date") or "", x.get("round", 0))):
        h, a, hg, ag = m["home"], m["away"], m["homeGoals"], m["awayGoals"]
        legs.append((h, a))
        for t in (h, a):
            if t not in teams:
                teams.append(t)
        if hg is not None and ag is not None:
            agg[h] += hg
            agg[a] += ag
        if m.get("homePens") is not None and m.get("awayPens") is not None:
            pens[h] = m["homePens"]
            pens[a] = m["awayPens"]

    if len(teams) != 2:
        return (teams[0] if teams else "", teams[1] if len(teams) > 1 else ""), None, legs
    a, b = teams
    winner: str | None = None
    if agg[a] != agg[b]:
        winner = a if agg[a] > agg[b] else b
    elif pens:
        winner = a if pens.get(a, 0) > pens.get(b, 0) else b
    return (a, b), winner, legs


def build_tree(ko_matches: list[dict]) -> tuple[Tie | None, list[Tie], list[str]]:
    """Group knockout matches into ties and wire the bracket tree.

    Returns ``(final_tie, all_ties, stages_present)``. The final tie is the tree
    root; following each tie's ``slots`` downward reaches the leaf entrants.
    """
    by_stage: dict[str, list[Tie]] = {s: [] for s in _STAGE_ORDER}
    grouped: dict[tuple[str, frozenset], list[dict]] = defaultdict(list)
    for m in ko_matches:
        st = m.get("stage", "")
        if st not in by_stage:
            continue
        grouped[(st, frozenset((m["home"], m["away"])))].append(m)

    all_ties: list[Tie] = []
    for (st, pair), ms in grouped.items():
        teams, winner, legs = _tie_winner(ms)
        tie = Tie(f"{st}:{'-'.join(sorted(pair))}", st, teams, winner, legs)
        by_stage[st].append(tie)
        all_ties.append(tie)

    stages_present = [s for s in _STAGE_ORDER if by_stage[s]]
    if not stages_present:
        return None, [], []

    # who won a tie in each stage → used to wire a later tie's entrants
    won_in: dict[str, dict[str, Tie]] = {
        s: {t.winner: t for t in by_stage[s] if t.winner} for s in stages_present
    }
    prev_stage = {stages_present[i]: stages_present[i - 1]
                  for i in range(1, len(stages_present))}

    def child_for(team: str, stage: str) -> Tie | None:
        ps = prev_stage.get(stage)
        if ps and team in won_in.get(ps, {}):
            return won_in[ps][team]
        return None  # seed / bye — enters here as a fixed leaf

    for st in stages_present:
        for tie in by_stage[st]:
            for team in tie.teams:
                child = child_for(team, st)
                tie.slots.append(("tie", child) if child else ("team", team))

    final_tie = by_stage["final"][0] if by_stage["final"] else by_stage[stages_present[-1]][0]
    return final_tie, all_ties, stages_present


# --------------------------------------------------------------------------- #
# Match / tie score model
# --------------------------------------------------------------------------- #
def _neutral_goals(elo_a: float, elo_b: float) -> tuple[float, float]:
    """Expected goals for a neutral-venue single match (no home advantage)."""
    supremacy = ((elo_a - elo_b) / 100.0) * GOALS_PER_100_ELO
    total = 2.0 * LEAGUE_AVG_GOALS
    la = float(np.clip(total / 2 + supremacy / 2, 0.15, MAX_LAMBDA))
    lb = float(np.clip(total / 2 - supremacy / 2, 0.15, MAX_LAMBDA))
    return la, lb


def _pen_pick(a: str, b: str, elo: dict[str, float], u: float) -> str:
    """Penalty shoot-out — a mild Elo tilt around a coin flip."""
    pa = 1.0 / (1.0 + 10 ** ((elo.get(b, 1500) - elo.get(a, 1500)) / 800.0))
    return a if u < pa else b


def _sim_tie(a: str, b: str, tie: Tie, elo: dict[str, float],
             gen: np.random.Generator) -> str:
    """Simulate one tie between resolved entrants ``a`` and ``b``."""
    if tie.neutral or len(tie.legs) <= 1:
        la, lb = _neutral_goals(elo.get(a, 1500), elo.get(b, 1500))
        ga, gb = gen.poisson(la), gen.poisson(lb)
        if ga != gb:
            return a if ga > gb else b
        return _pen_pick(a, b, elo, gen.random())
    # two legs — a hosts first, b hosts second (home advantage cancels)
    lh1, la1 = _expected_goals(elo.get(a, 1500), elo.get(b, 1500))
    lh2, la2 = _expected_goals(elo.get(b, 1500), elo.get(a, 1500))
    agg_a = gen.poisson(lh1) + gen.poisson(la2)
    agg_b = gen.poisson(la1) + gen.poisson(lh2)
    if agg_a != agg_b:
        return a if agg_a > agg_b else b
    return _pen_pick(a, b, elo, gen.random())


def _resolve_slot(slot, fixed: dict[str, str], elo, gen, cache) -> str:
    kind, val = slot
    if kind == "team":
        return val
    return _eval_tie(val, fixed, elo, gen, cache)


def _eval_tie(tie: Tie, fixed: dict[str, str], elo, gen, cache) -> str:
    if tie is None:
        return ""
    if tie.id in cache:
        return cache[tie.id]
    if tie.id in fixed:
        cache[tie.id] = fixed[tie.id]
        return fixed[tie.id]
    a = _resolve_slot(tie.slots[0], fixed, elo, gen, cache)
    b = _resolve_slot(tie.slots[1], fixed, elo, gen, cache)
    if not a or not b:
        winner = a or b
    else:
        winner = _sim_tie(a, b, tie, elo, gen)
    cache[tie.id] = winner
    return winner


def _run_mc(final_tie: Tie, fixed: dict[str, str], elo: dict[str, float],
            n_sims: int, gen: np.random.Generator) -> dict[str, float]:
    counts: dict[str, int] = defaultdict(int)
    for _ in range(n_sims):
        champ = _eval_tie(final_tie, fixed, elo, gen, {})
        if champ:
            counts[champ] += 1
    return {c: counts[c] / n_sims for c in counts}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def championship(codes: list[str], elo: dict[str, float],
                 ko_matches: list[dict]) -> dict:
    """Championship probabilities + the real champion + a convergence timeline.

    ``elo`` maps club code → current strength Elo. ``ko_matches`` are the
    tournament's knockout matches (stage != "league").
    """
    empty = {"odds": {c: 0.0 for c in codes},
             "currentOdds": {c: 0.0 for c in codes}, "champion": None,
             "stages": [], "timeline": _empty_timeline(codes)}
    final_tie, all_ties, stages = build_tree(ko_matches)
    if final_tie is None:
        return empty

    gen = np.random.default_rng(SEED)

    # bracket-set odds: nothing fixed, simulate the whole tree from Elo. This is
    # the *pre-knockout* forecast — useful as the timeline's opening snapshot.
    odds = _run_mc(final_tie, {}, elo, N_SIMS, gen)
    odds = {c: round(float(odds.get(c, 0.0)), 4) for c in codes}

    # current odds: fix every tie already decided to its real winner and simulate
    # only what remains. This reflects the tournament's *present* state, so a
    # finished bracket collapses to the actual champion at 100% (and everyone
    # else 0%) instead of the stale pre-knockout forecast. This is what the app
    # shows as the live "trophy chance".
    fixed_now = {t.id: t.winner for t in all_ties if t.winner}
    current = _run_mc(final_tie, fixed_now, elo, N_SIMS, gen)
    current = {c: round(float(current.get(c, 0.0)), 4) for c in codes}

    # actual champion, if the final has been decided
    champion = final_tie.winner

    timeline = _timeline(codes, elo, final_tie, all_ties, stages)
    return {"odds": odds, "currentOdds": current, "champion": champion,
            "stages": stages, "timeline": timeline}


def _empty_timeline(codes: list[str]) -> dict:
    return {"checkpoints": [], "labels": [], "series": {c: [] for c in codes},
            "lastCheckpoint": 0}


def _timeline(codes: list[str], elo: dict[str, float], final_tie: Tie,
              all_ties: list[Tie], stages: list[str]) -> dict:
    """Championship probability at 'bracket set' then after each knockout round.

    At checkpoint *k* every tie in stages ``0..k`` is fixed to its real winner
    and the remainder simulated, so the series converges to the actual champion.
    """
    ties_by_stage: dict[str, list[Tie]] = defaultdict(list)
    for t in all_ties:
        ties_by_stage[t.stage].append(t)

    gen = np.random.default_rng(SEED + 1)
    labels = ["Bracket set"]
    # only include a checkpoint for a stage once its ties are actually decided
    decided_stages = [s for s in stages if all(t.winner for t in ties_by_stage[s])]

    series: dict[str, list[float]] = {c: [] for c in codes}
    checkpoints: list[int] = [0]

    # k = 0 : bracket set (nothing fixed)
    snap = _run_mc(final_tie, {}, elo, RACE_N_SIMS, gen)
    for c in codes:
        series[c].append(round(float(snap.get(c, 0.0)) * 100, 2))

    fixed: dict[str, str] = {}
    for i, st in enumerate(decided_stages, start=1):
        for t in ties_by_stage[st]:
            if t.winner:
                fixed[t.id] = t.winner
        snap = _run_mc(final_tie, dict(fixed), elo, RACE_N_SIMS, gen)
        for c in codes:
            series[c].append(round(float(snap.get(c, 0.0)) * 100, 2))
        checkpoints.append(i)
        labels.append(_STAGE_LABEL.get(st, st.title()))

    return {"checkpoints": checkpoints, "labels": labels, "series": series,
            "lastCheckpoint": checkpoints[-1] if checkpoints else 0}
