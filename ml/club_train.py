"""
club_train.py  —  stage 4: model training (leakage-free)
========================================================
Trains the statistical / ML models on the **training corpus** only — completed
matches from seasons strictly earlier than the target season (see club_ingest).
Because the corpus never contains a target-season match, the resulting models can
score the whole target season without leaking any result into a feature.

Models produced per (league, season):
  * ``logreg``   multinomial logistic regression (standardised features)
  * ``forest``   random forest classifier
  * ``xgb``      gradient boosting (XGBoost) — falls back to sklearn GBDT if absent
  * ``draw``     the auxiliary binary draw model used by the Elo baseline

Artefacts are written to ``ml/models/{league}-{season}/`` as joblib files plus a
``meta.json`` describing the training set. The Elo baseline and market baseline
are analytic (no fitting) and are produced at predict time.
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import club_ingest as I
from club_features import FEATURE_ORDER, build_training_matrix
from club_modeling import elo_effective_diff
from leagues import MODELS_DIR, SEED

try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_XGB = False


def _model_dir(league_id: str, season_id: str) -> str:
    d = os.path.join(MODELS_DIR, f"{league_id}-{season_id}")
    os.makedirs(d, exist_ok=True)
    return d


def _build_logreg() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, C=1.0)),
    ])


def _build_forest() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=400, max_depth=8, min_samples_leaf=12,
        max_features="sqrt", random_state=SEED, n_jobs=-1)


def _build_xgb():
    if _HAS_XGB:
        return XGBClassifier(
            n_estimators=350, max_depth=4, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.85, reg_lambda=1.2,
            objective="multi:softprob", num_class=3,
            eval_metric="mlogloss", random_state=SEED, n_jobs=-1, verbosity=0)
    return GradientBoostingClassifier(random_state=SEED)


def _fit_draw_model(X: np.ndarray, y: np.ndarray) -> LogisticRegression:
    """Binary model P(draw) as a function of |effective Elo gap| — closer games
    draw more often. Used by the analytic Elo baseline."""
    eff = np.abs(elo_effective_diff(X)).reshape(-1, 1)
    is_draw = (y == 1).astype(int)
    return LogisticRegression(max_iter=1000).fit(eff, is_draw)


def train_combo(league_id: str, season_id: str) -> dict:
    ing = I.main(league_id, season_id)
    corpus = ing["corpus"]
    X, y, _ = build_training_matrix(corpus)
    if len(X) < 100:
        raise SystemExit(f"training corpus too small for {league_id} {season_id}: {len(X)}")

    models = {
        "logreg": _build_logreg().fit(X, y),
        "forest": _build_forest().fit(X, y),
        "xgb": _build_xgb().fit(X, y),
        "draw": _fit_draw_model(X, y),
    }

    d = _model_dir(league_id, season_id)
    for name, mdl in models.items():
        joblib.dump(mdl, os.path.join(d, f"{name}.joblib"))

    meta = {
        "league": league_id, "season": season_id,
        "trainingMatches": int(len(X)),
        "features": FEATURE_ORDER,
        "classBalance": {"home": int((y == 0).sum()),
                         "draw": int((y == 1).sum()),
                         "away": int((y == 2).sum())},
        "xgbBackend": "xgboost" if _HAS_XGB else "sklearn-gbdt",
    }
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    print(f"  [train] {league_id} {season_id}: fitted "
          f"{', '.join(k for k in models)} on {len(X)} matches "
          f"({meta['xgbBackend']})")
    return meta


if __name__ == "__main__":
    from leagues import COMBOS
    for lg, sn in COMBOS:
        train_combo(lg, sn)
