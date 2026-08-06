"""
club_simulate.py  —  stage 6: Monte-Carlo season simulation
===========================================================
Turns per-match predictions into the season-long questions fans actually ask:

  * who wins the title?
  * who finishes in the Champions-League / Europa places?
  * who gets relegated?
  * where does each club finish (full position distribution)?

Method: completed matches are **fixed** to their real results; each remaining
fixture is sampled from an independent-Poisson score model whose expected goals
come from the current Elo gap (home advantage baked in). We run many seasons,
rank every simulated table by (points, goal-difference, goals-for), and average
the outcomes. Clubs that are already **mathematically** unable to reach a bracket
are hard-zeroed (e.g. an eliminated side has a 0 % title chance), satisfying the
"eliminated ⇒ 0 %" requirement exactly rather than approximately.
"""
from __future__ import annotations

import numpy as np

from leagues import HOME_ADV, LEAGUE_AVG_GOALS, SEED

N_SIMS = 8000
GOALS_PER_100_ELO = 0.45   # goal supremacy added per 100 Elo of edge
MAX_LAMBDA = 5.0


def _expected_goals(elo_h: float, elo_a: float) -> tuple[float, float]:
    eff = (elo_h + HOME_ADV) - elo_a
    supremacy = (eff / 100.0) * GOALS_PER_100_ELO
    total = 2.0 * LEAGUE_AVG_GOALS
    lh = float(np.clip(total / 2 + supremacy / 2, 0.15, MAX_LAMBDA))
    la = float(np.clip(total / 2 - supremacy / 2, 0.15, MAX_LAMBDA))
    return lh, la


def _base_standings(codes: list[str], completed: list[dict]) -> dict[str, dict]:
    base = {c: {"pts": 0, "gf": 0, "ga": 0, "played": 0} for c in codes}
    for m in completed:
        h, a = m["home"], m["away"]
        hg, ag = m["homeGoals"], m["awayGoals"]
        if h not in base or a not in base:
            continue
        base[h]["gf"] += hg; base[h]["ga"] += ag; base[h]["played"] += 1
        base[a]["gf"] += ag; base[a]["ga"] += hg; base[a]["played"] += 1
        if hg > ag:
            base[h]["pts"] += 3
        elif hg < ag:
            base[a]["pts"] += 3
        else:
            base[h]["pts"] += 1; base[a]["pts"] += 1
    return base


def _max_possible(base: dict[str, dict], remaining_count: dict[str, int]) -> dict[str, int]:
    return {c: base[c]["pts"] + 3 * remaining_count.get(c, 0) for c in base}


def simulate(codes: list[str], elo: dict[str, float], completed: list[dict],
             remaining: list[dict], *, ucl: int, europa: int, releg: int,
             n_sims: int = N_SIMS) -> dict:
    """Return per-club season-outcome probabilities and expected finish."""
    codes = [c for c in codes if not c.startswith("~")]
    idx = {c: i for i, c in enumerate(codes)}
    n = len(codes)
    gen = np.random.default_rng(SEED)

    base = _base_standings(codes, completed)
    base_pts = np.array([base[c]["pts"] for c in codes], dtype=float)
    base_gd = np.array([base[c]["gf"] - base[c]["ga"] for c in codes], dtype=float)
    base_gf = np.array([base[c]["gf"] for c in codes], dtype=float)

    rem = [(idx[m["home"]], idx[m["away"]],
            *_expected_goals(m.get("_elo_home", elo.get(m["home"], 1500)),
                             m.get("_elo_away", elo.get(m["away"], 1500))))
           for m in remaining if m["home"] in idx and m["away"] in idx]

    rem_count: dict[str, int] = {c: 0 for c in codes}
    for m in remaining:
        if m["home"] in rem_count:
            rem_count[m["home"]] += 1
        if m["away"] in rem_count:
            rem_count[m["away"]] += 1

    champ = np.zeros(n); top_ucl = np.zeros(n); top_eu = np.zeros(n)
    releg_c = np.zeros(n); pos_hist = np.zeros((n, n)); pts_sum = np.zeros(n)

    # tiny deterministic jitter breaks exact ties without biasing ranks
    jitter = gen.random(n) * 1e-6

    for _ in range(n_sims):
        pts = base_pts.copy(); gd = base_gd.copy(); gf = base_gf.copy()
        for hi, ai, lh, la in rem:
            hgo = gen.poisson(lh); ago = gen.poisson(la)
            gf[hi] += hgo; gf[ai] += ago
            gd[hi] += hgo - ago; gd[ai] += ago - hgo
            if hgo > ago:
                pts[hi] += 3
            elif hgo < ago:
                pts[ai] += 3
            else:
                pts[hi] += 1; pts[ai] += 1
        # rank: points, then GD, then GF (universal tiebreak)
        key = pts * 1e6 + gd * 1e3 + gf + jitter
        order = np.argsort(-key)
        pts_sum += pts
        for rank, team in enumerate(order):
            pos_hist[team, rank] += 1
        champ[order[0]] += 1
        top_ucl[order[:ucl]] += 1
        top_eu[order[:europa]] += 1
        releg_c[order[n - releg:]] += 1

    max_pts = _max_possible(base, rem_count)
    lead_now = float(base_pts.max()) if n else 0.0

    out = {}
    for c in codes:
        i = idx[c]
        # hard mathematical elimination from the title race
        can_win = max_pts[c] >= lead_now
        title_p = float(champ[i] / n_sims) if can_win else 0.0
        out[c] = {
            "title": round(title_p, 4),
            "ucl": round(float(top_ucl[i] / n_sims), 4),
            "europa": round(float(top_eu[i] / n_sims), 4),
            "relegation": round(float(releg_c[i] / n_sims), 4),
            "expectedPoints": round(float(pts_sum[i] / n_sims), 1),
            "expectedPosition": round(float(
                sum((r + 1) * pos_hist[i, r] for r in range(n)) / n_sims), 2),
            "positionDist": [round(float(pos_hist[i, r] / n_sims), 4) for r in range(n)],
            "maxPoints": int(max_pts[c]),
            "canWinTitle": bool(can_win),
        }
    return out


# --------------------------------------------------------------------------- #
# Title-race timeline  (how the champion forecast evolves matchday by matchday)
# --------------------------------------------------------------------------- #
RACE_N_SIMS = 4000  # lighter than the headline sim: run once per matchday


def _title_counts(base_pts: np.ndarray, base_gd: np.ndarray, base_gf: np.ndarray,
                  rem: list[tuple], n: int, n_sims: int, gen: np.random.Generator,
                  jitter: np.ndarray) -> np.ndarray:
    """Vectorised Monte-Carlo → champion counts per club for one checkpoint.

    ``rem`` is a list of ``(home_idx, away_idx, lambda_home, lambda_away)`` for
    the still-to-play fixtures. We draw every remaining scoreline for all
    simulated seasons in one shot, scatter-add points/GD/GF onto the banked
    base standings, rank each simulated table by (pts, GD, GF) and tally the
    winner. Much faster than a Python double loop, so we can afford to re-run it
    for every matchday of the season.
    """
    if not rem:
        # nothing left to play → the current table is final (deterministic)
        key = base_pts * 1e6 + base_gd * 1e3 + base_gf + jitter
        counts = np.zeros(n)
        counts[int(np.argmax(key))] = n_sims
        return counts

    hi = np.array([r[0] for r in rem]); ai = np.array([r[1] for r in rem])
    lh = np.array([r[2] for r in rem]); la = np.array([r[3] for r in rem])

    hg = gen.poisson(lh, size=(n_sims, len(rem)))
    ag = gen.poisson(la, size=(n_sims, len(rem)))
    hpts = np.where(hg > ag, 3, np.where(hg == ag, 1, 0))
    apts = np.where(ag > hg, 3, np.where(hg == ag, 1, 0))
    gdiff = hg - ag

    pts = np.tile(base_pts, (n_sims, 1)).astype(float)
    gd = np.tile(base_gd, (n_sims, 1)).astype(float)
    gf = np.tile(base_gf, (n_sims, 1)).astype(float)
    rows = np.arange(n_sims)[:, None]
    np.add.at(pts, (rows, hi[None, :]), hpts)
    np.add.at(pts, (rows, ai[None, :]), apts)
    np.add.at(gd, (rows, hi[None, :]), gdiff)
    np.add.at(gd, (rows, ai[None, :]), -gdiff)
    np.add.at(gf, (rows, hi[None, :]), hg)
    np.add.at(gf, (rows, ai[None, :]), ag)

    key = pts * 1e6 + gd * 1e3 + gf + jitter[None, :]
    champ_idx = key.argmax(axis=1)
    return np.bincount(champ_idx, minlength=n).astype(float)


def _elo_snapshotter(codes: list[str], idx: dict[str, int], ordered: list[dict]):
    """Return ``elo_at(code, k)`` = a club's Elo *after* matchday ``k``.

    We use the pre-match Elo stored on the club's first fixture with round > k
    (its next game), which equals its current rating once every game up to and
    including matchday k has been played. Freezing the rating at the checkpoint
    is what makes early-season forecasts appropriately uncertain and late-season
    ones sharpen toward the eventual champion.
    """
    events: dict[str, list[tuple]] = {c: [] for c in codes}
    for m in ordered:
        h, a = m["home"], m["away"]
        order_key = m.get("datetime") or m.get("date") or ""
        if h in idx:
            events[h].append((m["round"], order_key, m.get("_elo_home", 1500.0)))
        if a in idx:
            events[a].append((m["round"], order_key, m.get("_elo_away", 1500.0)))
    for c in events:
        events[c].sort(key=lambda e: (e[0], e[1]))

    def elo_at(code: str, k: int) -> float:
        evs = events.get(code) or []
        for rnd, _, elo in evs:
            if rnd > k:
                return float(elo)
        return float(evs[-1][2]) if evs else 1500.0

    return elo_at


def title_race_timeline(codes: list[str], ordered: list[dict], *,
                        n_sims: int = RACE_N_SIMS) -> dict:
    """Champion probability for every club at every matchday checkpoint.

    Returns ``{"checkpoints": [0..L], "playedAt": [...], "maxRound": R,
    "lastCompletedRound": L, "series": {code: [prob0..1, ...]}}``. For a season
    with no completed matches yet (pre-season) the timeline is empty — there is
    nothing to trace until real results arrive.
    """
    codes = [c for c in codes if not c.startswith("~")]
    idx = {c: i for i, c in enumerate(codes)}
    n = len(codes)
    empty = {"checkpoints": [], "playedAt": [], "maxRound": 0,
             "lastCompletedRound": 0, "series": {c: [] for c in codes}}
    if n == 0:
        return empty

    in_field = [m for m in ordered if m["home"] in idx and m["away"] in idx]
    completed = [m for m in in_field if m.get("status") == "completed"]
    if not completed:
        return empty

    max_round = max(m["round"] for m in in_field)
    last_completed_round = max(m["round"] for m in completed)

    gen = np.random.default_rng(SEED)
    jitter = gen.random(n) * 1e-6
    elo_at = _elo_snapshotter(codes, idx, ordered)

    checkpoints = list(range(0, last_completed_round + 1))
    series: dict[str, list[float]] = {c: [] for c in codes}
    played_at: list[int] = []

    for k in checkpoints:
        fixed = [m for m in completed if m["round"] <= k]
        remaining = [m for m in in_field
                     if not (m.get("status") == "completed" and m["round"] <= k)]
        played_at.append(len(fixed))

        base = _base_standings(codes, fixed)
        base_pts = np.array([base[c]["pts"] for c in codes], dtype=float)
        base_gd = np.array([base[c]["gf"] - base[c]["ga"] for c in codes], dtype=float)
        base_gf = np.array([base[c]["gf"] for c in codes], dtype=float)

        elo_k = {c: elo_at(c, k) for c in codes}
        rem = [(idx[m["home"]], idx[m["away"]],
                *_expected_goals(elo_k[m["home"]], elo_k[m["away"]]))
               for m in remaining]
        counts = _title_counts(base_pts, base_gd, base_gf, rem, n, n_sims, gen, jitter)

        rem_count: dict[str, int] = {c: 0 for c in codes}
        for m in remaining:
            rem_count[m["home"]] += 1
            rem_count[m["away"]] += 1
        lead_now = float(base_pts.max())
        for c in codes:
            can_win = base[c]["pts"] + 3 * rem_count[c] >= lead_now
            p = float(counts[idx[c]] / n_sims) if can_win else 0.0
            series[c].append(round(p, 4))

    return {"checkpoints": checkpoints, "playedAt": played_at,
            "maxRound": max_round, "lastCompletedRound": last_completed_round,
            "series": series}
