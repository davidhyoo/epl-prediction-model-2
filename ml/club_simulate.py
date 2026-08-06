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
