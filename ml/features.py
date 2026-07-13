"""
features.py  —  Stage 3: feature engineering
=============================================
Builds pre-match features for every match (real history + World Cup). All
features are computed from information available *before kick-off* (rolling Elo,
form, goals, xG, rest days, head-to-head), so there is no target leakage:

  * real internationals (martj42)  -> rolling Elo/form state for EVERY nation
  * WC-vs-WC internationals ≥ 2002  -> TRAINING rows (X, y)
  * 2026 WC matches                 -> PREDICTION rows (X; y only if completed)

Real Elo is grown by walking the *entire* history from a common 1500 baseline
(World-Football-Elo style) — the pre-tournament rating of every 2026 side is
therefore earned purely from real results, never hand-set. Squad-strength /
attack / defense scores come from the generated squads, and team Elo is
snapshotted at each completed stage (used for the champion-odds trend).
Outputs land in data/processed.
"""
from __future__ import annotations

import os
from collections import defaultdict, deque
from datetime import datetime, timezone

import numpy as np

from common import (
    PROCESSED_DIR, read_json, write_json, write_json_pretty, FEATURE_ORDER,
    HOME_ADV, ELO_K, LEAGUE_AVG_GOALS, expected_goals, elo_win_prob,
    scale_0_100, clamp, rng,
)

# Only real World-Cup-vs-World-Cup matches from this year on become training
# rows, so the squad-strength feature (a 2026-squad quantity) stays meaningful
# and consistent between training and prediction.
TRAIN_SINCE = datetime(2002, 1, 1, tzinfo=timezone.utc)
BASELINE_ELO = 1500.0

# Completed stages, in chronological order, that we snapshot Elo after.
STAGE_ORDER = ["group", "round-of-32", "round-of-16", "quarter-final",
               "semi-final", "third-place", "final"]


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
    """Update Elo from the on-pitch result. ``home_adv`` is signed
    (-1/0/+1) so hosting the away side correctly *subtracts* the bonus. A tie on
    the given score (e.g. a penalty-shootout knockout) scores 0.5 for each."""
    bonus = HOME_ADV * home_adv
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
    codes = [t["code"] for t in teams]

    gen = rng("xg")
    # Every nation starts from a common baseline; real Elo is earned by walking
    # the full history. The 48 finalists are seeded so snapshots always resolve.
    state: dict[str, TeamState] = {c: TeamState(BASELINE_ELO) for c in codes}

    def get_state(key: str) -> TeamState:
        s = state.get(key)
        if s is None:
            s = TeamState(BASELINE_ELO)
            state[key] = s
        return s

    h2h_store: dict[tuple, list] = defaultdict(list)

    def h2h_avg(home: str, away: str) -> float:
        rec = h2h_store[tuple(sorted((home, away)))]
        if not rec:
            return 0.0
        vals = [gd if hc == home else -gd for (hc, gd) in rec]
        return float(np.mean(vals))

    def synth_xg(g_for: int, elo_for: float, elo_against: float, bonus: float) -> float:
        exp, _ = expected_goals(elo_for + bonus, elo_against)
        return float(clamp(0.62 * g_for + 0.38 * exp + gen.normal(0, 0.33), 0.1, 6.0))

    def snapshot() -> dict:
        return {c: round(state[c].elo, 1) for c in codes}

    # ---- History walk: real Elo/form for all nations + training rows --------
    train_X, train_y = [], []
    for m in history:
        hk, ak = m["home"], m["away"]
        sh, sa = get_state(hk), get_state(ak)
        date = datetime.fromisoformat(m["date"])
        is_train = (m["home_code"] and m["away_code"] and date >= TRAIN_SINCE)
        if is_train:
            row = _feature_row(sh, sa, m["home_adv"], 0, h2h_avg(hk, ak), date,
                               squad_score.get(m["home_code"], 50.0),
                               squad_score.get(m["away_code"], 50.0))
            train_X.append(_vec(row))
            train_y.append(m["outcome"])
        bonus = HOME_ADV * m["home_adv"]
        xg_h = synth_xg(m["gh"], sh.elo, sa.elo, bonus)
        xg_a = synth_xg(m["ga"], sa.elo, sh.elo, 0.0)
        _elo_update(sh, sa, m["fh"], m["fa"], m["home_adv"], k=24.0)
        _push_result(sh, m["gh"], m["ga"], xg_h, date)
        _push_result(sa, m["ga"], m["gh"], xg_a, date)
        h2h_store[tuple(sorted((hk, ak)))].append((hk, m["gh"] - m["ga"]))

    elo_pre = snapshot()
    elo_snapshots = {"pre": elo_pre}

    # ---- 2026 World Cup: process completed matches in stage/chrono order ----
    wc_features = []

    def process_completed(m):
        h, a = m["home"], m["away"]
        sh, sa = get_state(h), get_state(a)
        date = datetime.fromisoformat(m["date"])
        row = _feature_row(sh, sa, m["home_adv"], m["knockout"], h2h_avg(h, a),
                           date, squad_score.get(h, 50.0), squad_score.get(a, 50.0))
        wc_features.append({
            "id": m["id"], "stage": m["stage"], "knockout": m["knockout"],
            "status": m["status"], "home": h, "away": a,
            "X": _vec(row), "feats": {kk: round(vv, 4) for kk, vv in row.items()},
            "y": m["outcome"],
        })
        bonus = HOME_ADV * m["home_adv"]
        xg_h = synth_xg(m["gh"], sh.elo, sa.elo, bonus)
        xg_a = synth_xg(m["ga"], sa.elo, sh.elo, 0.0)
        _elo_update(sh, sa, m["fh"], m["fa"], m["home_adv"], k=ELO_K)
        _push_result(sh, m["gh"], m["ga"], xg_h, date)
        _push_result(sa, m["ga"], m["gh"], xg_a, date)
        h2h_store[tuple(sorted((h, a)))].append((h, m["gh"] - m["ga"]))

    completed = [m for m in wc if m["status"] == "completed"]
    by_stage: dict[str, list] = defaultdict(list)
    for m in completed:
        by_stage[m["stage"]].append(m)
    for stage in STAGE_ORDER:
        ms = sorted(by_stage.get(stage, []),
                    key=lambda x: (x["date"], x["slot"] if x["slot"] is not None else 0))
        for m in ms:
            process_completed(m)
        if ms:
            elo_snapshots[stage] = snapshot()

    elo_current = snapshot()

    # team rolling snapshot at the current tournament state (form/strength cards)
    team_form = {c: {
        "form_ppg": round(state[c].form(), 3),
        "gf_recent": round(state[c].avg_gf(), 3),
        "ga_recent": round(state[c].avg_ga(), 3),
        "xg_recent": round(state[c].avg_xg(), 3),
        "momentum": round(state[c].momentum(), 3),
    } for c in codes}

    # ---- Upcoming matches with known teams: features only (no state update) -
    upcoming_known = [m for m in wc
                      if m["status"] != "completed" and m["home"] and m["away"]]
    upcoming_known.sort(key=lambda x: (x["date"], x["num"] if x["num"] is not None else 0))
    for m in upcoming_known:
        h, a = m["home"], m["away"]
        sh, sa = get_state(h), get_state(a)
        date = datetime.fromisoformat(m["date"])
        row = _feature_row(sh, sa, m["home_adv"], m["knockout"], h2h_avg(h, a),
                           date, squad_score.get(h, 50.0), squad_score.get(a, 50.0))
        wc_features.append({
            "id": m["id"], "stage": m["stage"], "knockout": m["knockout"],
            "status": m["status"], "home": h, "away": a,
            "X": _vec(row), "feats": {kk: round(vv, 4) for kk, vv in row.items()},
            "y": None,
        })

    write_json_pretty(os.path.join(PROCESSED_DIR, "train.json"),
                      {"feature_order": FEATURE_ORDER, "X": train_X, "y": train_y})
    write_json_pretty(os.path.join(PROCESSED_DIR, "wc_features.json"), {
        "feature_order": FEATURE_ORDER,
        "matches": wc_features,
        "elo_current": elo_current,
        "elo_pre": elo_pre,
        "elo_snapshots": elo_snapshots,
    })
    write_json_pretty(os.path.join(PROCESSED_DIR, "team_strength.json"), {
        "strength": strength, "form": team_form,
        "elo_current": elo_current, "elo_pre": elo_pre,
    })

    print(f"[features] train_rows={len(train_X)} wc_rows={len(wc_features)} "
          f"(completed={sum(1 for r in wc_features if r['y'] is not None)}) "
          f"snapshots={list(elo_snapshots)}")


def main() -> None:
    build_features()


if __name__ == "__main__":
    main()
