"""
club_features.py  —  stage 3: leakage-safe feature engineering
==============================================================
A single chronological "engine" walks every match in date order and, for each
fixture, emits a feature vector computed **only from matches that kicked off
before it**. Completed matches then update the running state (Elo, rolling form,
head-to-head); upcoming matches never do. This guarantees no target leaks into a
feature — the cornerstone of an honest backtest.

Features (all oriented home-minus-away, so a positive value favours the home team):

    elo_diff       home Elo − away Elo (Elo grown from real results since 2020)
    home_adv       constant 1.0 — lets the models learn the home-field effect
    form_diff      points-per-game over the last 5 (home − away)
    attack_diff    average goals scored, last 6 (home − away)
    defense_diff   average goals conceded, last 6 (away − home ⇒ +ve = home tighter)
    sot_diff       average shots on target for, last 6 (home − away)
    rest_diff      days of rest, clipped ±7 and scaled (home − away)
    h2h_diff       average home-perspective goal difference over recent meetings

Elo is regressed 25 % toward the 1500 baseline across the summer break (a > 60-day
gap) to reflect squad turnover; clubs with no recent top-flight history enter at
a below-average prior.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date

import numpy as np

from leagues import ELO_BASELINE, ELO_K, HOME_ADV

FEATURE_ORDER = [
    "elo_diff", "home_adv", "form_diff", "attack_diff",
    "defense_diff", "sot_diff", "rest_diff", "h2h_diff",
]
FEATURE_LABELS = {
    "elo_diff": "Elo rating gap",
    "home_adv": "Home advantage",
    "form_diff": "Recent form (pts/game)",
    "attack_diff": "Attacking output",
    "defense_diff": "Defensive solidity",
    "sot_diff": "Shots on target trend",
    "rest_diff": "Rest days",
    "h2h_diff": "Head-to-head record",
}
N_FEATURES = len(FEATURE_ORDER)

FORM_WINDOW = 5
STAT_WINDOW = 6
PROMOTED_ELO = 1440.0
SEASON_GAP_DAYS = 60
REGRESSION = 0.25  # fraction pulled back to the mean each summer


def _iso_to_date(s: str | None) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s[:10])


def outcome_label(hg: int, ag: int) -> int:
    """0 = home win, 1 = draw, 2 = away win."""
    return 0 if hg > ag else (1 if hg == ag else 2)


class FeatureEngine:
    """Stateful, chronological feature builder (see module docstring)."""

    def __init__(self) -> None:
        self.elo: dict[str, float] = {}
        self.gf: dict[str, deque] = defaultdict(lambda: deque(maxlen=STAT_WINDOW))
        self.ga: dict[str, deque] = defaultdict(lambda: deque(maxlen=STAT_WINDOW))
        self.sot: dict[str, deque] = defaultdict(lambda: deque(maxlen=STAT_WINDOW))
        self.pts: dict[str, deque] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
        self.last_played: dict[str, date] = {}
        self.h2h: dict[tuple, deque] = defaultdict(lambda: deque(maxlen=6))
        self.games: dict[str, int] = defaultdict(int)
        self._last_global: date | None = None

    # -- Elo -------------------------------------------------------------- #
    def _get_elo(self, code: str) -> float:
        if code not in self.elo:
            self.elo[code] = PROMOTED_ELO
        return self.elo[code]

    def _maybe_regress(self, d: date | None) -> None:
        if d is None or self._last_global is None:
            return
        if (d - self._last_global).days > SEASON_GAP_DAYS:
            for k in list(self.elo):
                self.elo[k] = (1 - REGRESSION) * self.elo[k] + REGRESSION * ELO_BASELINE

    # -- rolling helpers -------------------------------------------------- #
    @staticmethod
    def _avg(dq: deque, default: float) -> float:
        return float(np.mean(dq)) if len(dq) else default

    def _ppg(self, code: str) -> float:
        return self._avg(self.pts[code], 1.3)  # league-average-ish prior

    def _rest(self, code: str, d: date | None) -> float:
        lp = self.last_played.get(code)
        if lp is None or d is None:
            return 7.0
        return float((d - lp).days)

    # -- feature vector --------------------------------------------------- #
    def features(self, m: dict) -> np.ndarray:
        h, a = m["home"], m["away"]
        d = _iso_to_date(m.get("date"))
        self._maybe_regress(d)
        # advance the clock on *every* fixture (played or not) so the summer
        # mean-regression fires exactly once at the season boundary — otherwise an
        # unplayed season (which never calls observe) would regress on every match.
        if d is not None:
            self._last_global = d

        elo_diff = (self._get_elo(h) - self._get_elo(a)) / 100.0
        form_diff = self._ppg(h) - self._ppg(a)
        attack_diff = self._avg(self.gf[h], 1.3) - self._avg(self.gf[a], 1.3)
        defense_diff = self._avg(self.ga[a], 1.3) - self._avg(self.ga[h], 1.3)
        sot_diff = self._avg(self.sot[h], 4.5) - self._avg(self.sot[a], 4.5)
        rest_diff = float(np.clip(self._rest(h, d) - self._rest(a, d), -7, 7)) / 7.0

        hh = list(self.h2h[(h, a)])
        h2h_diff = float(np.mean(hh)) if hh else 0.0

        return np.array([
            elo_diff, 1.0, form_diff, attack_diff,
            defense_diff, sot_diff, rest_diff, h2h_diff,
        ], dtype=float)

    # -- state update ----------------------------------------------------- #
    def observe(self, m: dict) -> None:
        hg, ag = m.get("homeGoals"), m.get("awayGoals")
        if hg is None or ag is None:
            return
        h, a = m["home"], m["away"]
        d = _iso_to_date(m.get("date"))

        # Elo update with a goal-difference multiplier (World-Football-Elo style)
        eh, ea = self._get_elo(h), self._get_elo(a)
        exp_h = 1.0 / (1.0 + 10 ** (-((eh + HOME_ADV) - ea) / 400.0))
        res_h = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
        gd = abs(hg - ag)
        mult = 1.0 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8.0)
        delta = ELO_K * mult * (res_h - exp_h)
        self.elo[h] = eh + delta
        self.elo[a] = ea - delta

        # rolling stats
        self.gf[h].append(hg); self.ga[h].append(ag)
        self.gf[a].append(ag); self.ga[a].append(hg)
        # SOT lives at the top level for football-data history rows, but nested
        # under matchStats for merged season matches — accept either shape.
        sot = m.get("shotsOnTarget") or (m.get("matchStats") or {}).get("shotsOnTarget") or {}
        self.sot[h].append(sot.get("home") if sot.get("home") is not None else 4.5)
        self.sot[a].append(sot.get("away") if sot.get("away") is not None else 4.5)

        ph = 3 if hg > ag else (1 if hg == ag else 0)
        self.pts[h].append(ph)
        self.pts[a].append(3 if ag > hg else (1 if hg == ag else 0))

        self.h2h[(h, a)].append(hg - ag)
        self.h2h[(a, h)].append(ag - hg)

        if d is not None:
            self.last_played[h] = d
            self.last_played[a] = d
            self._last_global = d
        self.games[h] += 1
        self.games[a] += 1

    # -- convenience snapshots (for team strength) ------------------------ #
    def snapshot(self, code: str) -> dict:
        return {
            "elo": round(self._get_elo(code), 1),
            "gfAvg": round(self._avg(self.gf[code], 0.0), 3),
            "gaAvg": round(self._avg(self.ga[code], 0.0), 3),
            "sotAvg": round(self._avg(self.sot[code], 0.0), 3),
            "ppg": round(self._ppg(code), 3),
            "games": self.games[code],
        }


def build_training_matrix(corpus: list[dict]) -> tuple[np.ndarray, np.ndarray, "FeatureEngine"]:
    """Walk the (strictly-past) corpus, returning (X, y) and the primed engine."""
    eng = FeatureEngine()
    X, y = [], []
    for m in sorted(corpus, key=lambda r: r["date"] or ""):
        X.append(eng.features(m))
        y.append(outcome_label(m["homeGoals"], m["awayGoals"]))
        eng.observe(m)
    return np.asarray(X, dtype=float), np.asarray(y, dtype=int), eng


def build_season_features(eng: "FeatureEngine", matches: list[dict]) -> tuple[np.ndarray, list[dict]]:
    """Continue the primed engine through the target season (date order).

    Returns the feature matrix aligned to the returned (chronological) match list.
    Completed matches update the engine so later weeks reflect earlier results —
    the features stay leakage-free because each row is computed *before* observe().
    """
    ordered = sorted(matches, key=lambda r: (r.get("datetime") or r.get("date") or "",
                                             r["home"]))
    X = []
    for m in ordered:
        vec = eng.features(m)              # applies the season-boundary regression
        m["_elo_home"] = round(eng._get_elo(m["home"]), 1)
        m["_elo_away"] = round(eng._get_elo(m["away"]), 1)
        X.append(vec)
        eng.observe(m)
    return np.asarray(X, dtype=float), ordered
