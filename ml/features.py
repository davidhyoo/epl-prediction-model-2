"""
features.py  —  Stage 3: feature engineering
=============================================
Builds pre-match features for every match (history + World Cup). All features
are computed from information available *before kick-off* (rolling Elo, form,
goals, xG, rest days, head-to-head) so there is no target leakage:

  * history matches (2019-2025)  -> TRAINING rows (X, y)
  * WC matches                   -> PREDICTION rows (X, y only if completed)

Also derives squad-strength / attack / defense scores from the generated
squads and snapshots team Elo at several points (used for champion-odds
trends). Outputs land in data/processed.
"""
from __future__ import annotations

import os
from collections import defaultdict, deque
from datetime import datetime

import numpy as np

from common import (
    PROCESSED_DIR, read_json, write_json_pretty, FEATURE_ORDER,
    HOME_ADV, ELO_K, LEAGUE_AVG_GOALS, expected_goals, elo_win_prob,
    scale_0_100, clamp, rng,
)


# --------------------------------------------------------------------------- #
# Squad strength from generated players
# --------------------------------------------------------------------------- #
def compute_squad_strength(squads: list[dict], teams: list[dict]) -> dict:
    by_team: dict[str, list[dict]] = defaultdict(list)
    for p in squads:
        by_team[p["countryCode"]].append(p)

    raw = {}
    for code, players in by_team.items():
        players = sorted(players, key=lambda x: -x["rating"])
        starters = players[:11]
        subs = players[11:]
        overall = (np.mean([p["rating"] for p in starters]) * 0.78
                   + np.mean([p["rating"] for p in subs]) * 0.22)
        att = np.mean([p["rating"] for p in starters
                       if p["position"] in ("FWD", "MID")] or [70])
        dfn = np.mean([p["rating"] for p in starters
                       if p["position"] in ("GK", "DEF")] or [70])
        exp = np.mean([p["age"] for p in players])
        raw[code] = {"overall": float(overall), "attack": float(att),
                     "defense": float(dfn), "age": float(exp)}

    ov = [v["overall"] for v in raw.values()]
    at = [v["attack"] for v in raw.values()]
    de = [v["defense"] for v in raw.values()]
    lo_o, hi_o = min(ov), max(ov)
    lo_a, hi_a = min(at), max(at)
    lo_d, hi_d = min(de), max(de)

    strength = {}
    for code, v in raw.items():
        strength[code] = {
            "squad": scale_0_100(v["overall"], lo_o, hi_o),
            "attack": scale_0_100(v["attack"], lo_a, hi_a),
            "defense": scale_0_100(v["defense"], lo_d, hi_d),
            "experience": round(clamp((v["age"] - 24) / (30 - 24) * 100, 5, 99), 1),
            "squad_raw": round(v["overall"], 2),
        }
    return strength


# --------------------------------------------------------------------------- #
# Rolling-state feature builder
# --------------------------------------------------------------------------- #
class TeamState:
    __slots__ = ("elo", "results", "gf", "ga", "xg", "last_date", "streak_pts")

    def __init__(self, elo0: float):
        self.elo = elo0
        self.results = deque(maxlen=5)   # points 3/1/0
        self.gf = deque(maxlen=5)
        self.ga = deque(maxlen=5)
        self.xg = deque(maxlen=5)
        self.last_date: datetime | None = None
        self.streak_pts = deque(maxlen=3)

    def form(self) -> float:
        return float(np.mean(self.results)) if self.results else 1.2

    def avg_gf(self) -> float:
        return float(np.mean(self.gf)) if self.gf else LEAGUE_AVG_GOALS

    def avg_ga(self) -> float:
        return float(np.mean(self.ga)) if self.ga else LEAGUE_AVG_GOALS

    def avg_xg(self) -> float:
        return float(np.mean(self.xg)) if self.xg else LEAGUE_AVG_GOALS

    def momentum(self) -> float:
        return float(np.sum(self.streak_pts)) if self.streak_pts else 3.0


def _elo_update(state_h: TeamState, state_a: TeamState, gh: int, ga: int,
                home_adv: int, k: float) -> None:
    bonus = HOME_ADV if home_adv else 0.0
    exp_h = elo_win_prob(state_h.elo + bonus, state_a.elo)
    score_h = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
    gd = abs(gh - ga)
    k_eff = k * (1.0 + 0.35 * max(0, gd - 1))
    delta = k_eff * (score_h - exp_h)
    state_h.elo += delta
    state_a.elo -= delta


def _push_result(state: TeamState, gf: int, ga: int, xg: float,
                 date: datetime) -> None:
    pts = 3 if gf > ga else (1 if gf == ga else 0)
    state.results.append(pts)
    state.streak_pts.append(pts)
    state.gf.append(gf)
    state.ga.append(ga)
    state.xg.append(xg)
    state.last_date = date


def _rest_days(state: TeamState, date: datetime) -> float:
    if state.last_date is None:
        return 7.0
    return clamp((date - state.last_date).days, 2, 21)


def _feature_row(sh: TeamState, sa: TeamState, home_adv: int, knockout: int,
                 h2h: float, date: datetime, squad_h: float, squad_a: float
                 ) -> dict:
    return {
        "elo_diff": sh.elo - sa.elo,
        "form_diff": sh.form() - sa.form(),
        "gf_diff": sh.avg_gf() - sa.avg_gf(),
        "ga_diff": sa.avg_ga() - sh.avg_ga(),   # positive => home concedes fewer
        "xg_diff": sh.avg_xg() - sa.avg_xg(),
        "squad_diff": (squad_h - squad_a) / 10.0,
        "rest_diff": _rest_days(sh, date) - _rest_days(sa, date),
        "h2h_diff": h2h,
        "host_adv": float(home_adv),
        "stage_knockout": float(knockout),
    }


def _vec(row: dict) -> list[float]:
    return [round(float(row[f]), 4) for f in FEATURE_ORDER]


def build_features() -> None:
    teams = read_json(os.path.join(PROCESSED_DIR, "teams.json"))
    history = read_json(os.path.join(PROCESSED_DIR, "history.json"))
    wc = read_json(os.path.join(PROCESSED_DIR, "wc_matches.json"))
    squads = read_json(os.path.join(PROCESSED_DIR, "squads.json"))

    strength = compute_squad_strength(squads, teams)
    squad_score = {c: strength[c]["squad"] for c in strength}

    gen = rng("xg")
    state = {t["code"]: TeamState(t["elo0"]) for t in teams}
    h2h_store: dict[tuple, list] = defaultdict(list)

    def h2h_avg(home: str, away: str) -> float:
        key = tuple(sorted((home, away)))
        rec = h2h_store[key]
        if not rec:
            return 0.0
        vals = [gd if hc == home else -gd for (hc, gd) in rec]
        return float(np.mean(vals))

    def synth_xg(g_for: int, elo_for: float, elo_against: float, bonus: float) -> float:
        exp, _ = expected_goals(elo_for + bonus, elo_against)
        return float(clamp(0.62 * g_for + 0.38 * exp + gen.normal(0, 0.33), 0.1, 6.0))

    # ---- History (training) ----------------------------------------------
    train_X, train_y = [], []
    for m in history:
        h, a = m["home"], m["away"]
        sh, sa = state[h], state[a]
        date = datetime.fromisoformat(m["date"])
        row = _feature_row(sh, sa, m["home_adv"], 0, h2h_avg(h, a), date,
                           squad_score[h], squad_score[a])
        train_X.append(_vec(row))
        train_y.append(m["outcome"])
        # update state
        bonus = HOME_ADV if m["home_adv"] else 0.0
        xg_h = synth_xg(m["gh"], sh.elo, sa.elo, bonus)
        xg_a = synth_xg(m["ga"], sa.elo, sh.elo, 0.0)
        _elo_update(sh, sa, m["gh"], m["ga"], m["home_adv"], k=24.0)
        _push_result(sh, m["gh"], m["ga"], xg_h, date)
        _push_result(sa, m["ga"], m["gh"], xg_a, date)
        h2h_store[tuple(sorted((h, a)))].append((h, m["gh"] - m["ga"]))

    elo_pre = {c: round(s.elo, 1) for c, s in state.items()}

    # ---- WC group stage (completed) --------------------------------------
    group_matches = [m for m in wc if m["stage"] == "group"]
    group_matches.sort(key=lambda m: (m["matchday"], m["group"]))
    knockout_matches = [m for m in wc if m["stage"] != "group"]
    stage_rank = {"round-of-32": 0, "round-of-16": 1, "quarter-final": 2,
                  "semi-final": 3, "third-place": 4, "final": 5}
    knockout_matches.sort(key=lambda m: (stage_rank[m["stage"]], m["slot"]))

    wc_features = []
    elo_snapshots = {"pre": elo_pre}

    def process_wc(m, k):
        h, a = m["home"], m["away"]
        sh, sa = state[h], state[a]
        date = datetime.fromisoformat(m["date"])
        row = _feature_row(sh, sa, m["home_adv"], m["knockout"], h2h_avg(h, a),
                           date, squad_score[h], squad_score[a])
        wc_features.append({
            "id": m["id"], "stage": m["stage"], "knockout": m["knockout"],
            "status": m["status"], "home": h, "away": a,
            "X": _vec(row), "feats": {kk: round(vv, 4) for kk, vv in row.items()},
            "y": m["outcome"],
        })
        bonus = HOME_ADV if m["home_adv"] else 0.0
        xg_h = synth_xg(m["gh"], sh.elo, sa.elo, bonus)
        xg_a = synth_xg(m["ga"], sa.elo, sh.elo, 0.0)
        _elo_update(sh, sa, m["gh"], m["ga"], m["home_adv"], k=k)
        _push_result(sh, m["gh"], m["ga"], xg_h, date)
        _push_result(sa, m["ga"], m["gh"], xg_a, date)
        h2h_store[tuple(sorted((h, a)))].append((h, m["gh"] - m["ga"]))

    for md in (1, 2, 3):
        for m in [x for x in group_matches if x["matchday"] == md]:
            process_wc(m, k=ELO_K)
        elo_snapshots[f"md{md}"] = {c: round(s.elo, 1) for c, s in state.items()}

    elo_current = {c: round(s.elo, 1) for c, s in state.items()}

    # team rolling snapshot at end of group stage (for team strength/form)
    team_form = {}
    for c, s in state.items():
        team_form[c] = {
            "form_ppg": round(s.form(), 3),
            "gf_recent": round(s.avg_gf(), 3),
            "ga_recent": round(s.avg_ga(), 3),
            "xg_recent": round(s.avg_xg(), 3),
            "momentum": round(s.momentum(), 3),
        }

    # ---- WC knockout stage (upcoming: features only, no leakage into eval) -
    for m in knockout_matches:
        process_wc(m, k=ELO_K)

    write_json_pretty(os.path.join(PROCESSED_DIR, "train.json"),
                      {"feature_order": FEATURE_ORDER, "X": train_X, "y": train_y})
    write_json_pretty(os.path.join(PROCESSED_DIR, "wc_features.json"), {
        "feature_order": FEATURE_ORDER,
        "matches": wc_features,
        "elo_current": elo_current,
        "elo_snapshots": elo_snapshots,
    })
    write_json_pretty(os.path.join(PROCESSED_DIR, "team_strength.json"), {
        "strength": strength, "form": team_form,
        "elo_current": elo_current, "elo_pre": elo_pre,
    })

    print(f"[features] train_rows={len(train_X)} wc_rows={len(wc_features)} "
          f"features={len(FEATURE_ORDER)}")


def main() -> None:
    build_features()


if __name__ == "__main__":
    main()
