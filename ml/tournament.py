"""
tournament.py
=============
Real 2026 World Cup tournament logic shared by ingest (real group tables + the
real Round-of-32 bracket) and predict (the Monte-Carlo championship simulator).

Format: 48 teams, 12 groups of 4 -> 72 group matches. Top 2 of each group plus
the 8 best third-placed teams -> Round of 32 -> ... -> Final (104 matches). The
qualifiers and every bracket matchup come straight from the CC0 openfootball
source (see ml/sources.py) — nothing here is invented.

The simulator (``simulate_bracket``) is *stateful about reality*: any knockout
match that has already been played is FIXED to its real winner, and only the
remaining matches are simulated. This is what lets the app show honest live
title odds at any point in the tournament (currently the semi-finals).
"""
from __future__ import annotations

import numpy as np

from common import GROUPS


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


def group_tables(records: dict[str, dict], teams_by_code: dict) -> dict[str, list[str]]:
    """Return ordered list of team codes per group (best first) and stamp
    ``groupRank`` onto each record. Tiebreak: points, GD, GF, then Elo prior
    (an approximation of FIFA's head-to-head rules — the actual qualifiers come
    from the source data, so this only affects the displayed standings)."""
    tables: dict[str, list[str]] = {}
    for g in GROUPS:
        members = [c for c, t in teams_by_code.items() if t.group == g]
        members.sort(key=lambda c: rank_key(records[c], teams_by_code[c].elo0),
                     reverse=True)
        for rank, c in enumerate(members, start=1):
            records[c]["groupRank"] = rank
        tables[g] = members
    return tables


# --------------------------------------------------------------------------- #
# Vectorised Monte-Carlo championship simulator (respects completed results)
# --------------------------------------------------------------------------- #
STAGE_RANK = {"round-of-32": 0, "round-of-16": 1, "quarter-final": 2,
              "semi-final": 3, "third-place": 3, "final": 4}
# Stages that count towards a team's "advancement" milestones (3rd-place is a
# consolation match and is excluded — reaching the semi is already credited).
REACH_STAGES = ["round-of-32", "round-of-16", "quarter-final", "semi-final", "final"]
FINAL_NUM = 104


def _resolve(feed, fixed_code, winners, losers, idx_by_code, n_sims):
    """Resolve a match side to an (n_sims,) array of team indices."""
    if feed:
        kind, fnum = feed[0], int(feed[1])
        return winners[fnum] if kind == "W" else losers[fnum]
    return np.full(n_sims, idx_by_code[fixed_code], dtype=np.int64)


def simulate_bracket(knockout: list[dict], eff: np.ndarray, idx_by_code: dict,
                     n_sims: int, generator: np.random.Generator,
                     as_of_rank: int | None = None) -> dict:
    """
    Monte-Carlo the knockout bracket.

    knockout    : the qualification["knockout"] tree, each item with num, stage,
                  homeCode/awayCode, feedHome/feedAway ('W'|'L', num), played,
                  winnerSide (0 home / 2 away).
    eff         : (n_teams,) effective ratings.
    as_of_rank  : if given, treat only matches whose STAGE_RANK <= as_of_rank as
                  played (the rest are simulated) — used for champion-odds
                  history "rewound" to an earlier point. None => use reality.

    Returns dict:
      champion : (n_teams,) win counts
      reach    : {stage -> (n_teams,) participation counts}
      proj     : {num -> {homeIdx, awayIdx, homeWinFrac}} for simulated matches
    """
    n_teams = eff.shape[0]
    reach = {s: np.zeros(n_teams, dtype=np.int64) for s in REACH_STAGES}
    winners: dict[int, np.ndarray] = {}
    losers: dict[int, np.ndarray] = {}
    proj: dict[int, dict] = {}
    champion = np.zeros(n_teams, dtype=np.int64)

    for m in sorted(knockout, key=lambda x: x["num"]):
        num, stage = m["num"], m["stage"]
        played = m["played"] if as_of_rank is None else (
            m["played"] and STAGE_RANK[stage] <= as_of_rank)

        # For a match we treat as PLAYED, winnerSide is defined relative to the
        # real homeCode/awayCode, so we must resolve those exact fixed teams. For
        # a match we simulate, participants come from the bracket feeders (the
        # winners/losers of earlier matches) — or a fixed code for the R32 seeds.
        if played:
            home = np.full(n_sims, idx_by_code[m["homeCode"]], dtype=np.int64)
            away = np.full(n_sims, idx_by_code[m["awayCode"]], dtype=np.int64)
        else:
            home = _resolve(m["feedHome"], m["homeCode"], winners, losers, idx_by_code, n_sims)
            away = _resolve(m["feedAway"], m["awayCode"], winners, losers, idx_by_code, n_sims)

        if stage in reach:
            np.add.at(reach[stage], home, 1)
            np.add.at(reach[stage], away, 1)

        if played:
            if m["winnerSide"] == 0:
                win, lose = home, away
            else:
                win, lose = away, home
        else:
            ph = 1.0 / (1.0 + np.power(10.0, (eff[away] - eff[home]) / 400.0))
            home_wins = generator.random(n_sims) < ph
            win = np.where(home_wins, home, away)
            lose = np.where(home_wins, away, home)
            proj[num] = {
                "homeIdx": int(np.bincount(home, minlength=n_teams).argmax()),
                "awayIdx": int(np.bincount(away, minlength=n_teams).argmax()),
                "homeWinFrac": float(home_wins.mean()),
            }

        winners[num], losers[num] = win, lose
        if num == FINAL_NUM:
            np.add.at(champion, win, 1)

    return {"champion": champion, "reach": reach, "proj": proj}
