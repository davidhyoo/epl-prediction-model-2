"""
train.py  —  Stage 4: model training
=====================================
Trains the model zoo on the synthetic international history (2019-2025) ONLY,
so no World Cup match ever appears in training (leakage-free). Models:

  * Elo baseline      — analytic two-stage Elo (+ fitted draw model)
  * Logistic Regression (multinomial, standardised features)
  * Random Forest
  * XGBoost (gradient boosting)

A weighted ensemble is assembled later (predict/evaluate). Artifacts are saved
to ml/models. A time-based validation split is used only to print honest
sanity metrics; final models are refit on the full history.
"""
from __future__ import annotations

import os
import json

import numpy as np
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from common import (
    PROCESSED_DIR, MODELS_DIR, FEATURE_ORDER, SEED, read_json, now_iso,
)
from modeling import (
    elo_effective_diff, elo_baseline_proba, evaluate_model, normalize_importance,
)


def _load_train():
    data = read_json(os.path.join(PROCESSED_DIR, "train.json"))
    X = np.array(data["X"], dtype=float)
    y = np.array(data["y"], dtype=int)
    return X, y


def _fit_draw_model(X: np.ndarray, y: np.ndarray) -> LogisticRegression:
    """P(draw) as a function of |effective Elo difference|."""
    eff = np.abs(elo_effective_diff(X)).reshape(-1, 1)
    is_draw = (y == 1).astype(int)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(eff, is_draw)
    return clf


def _build_models():
    logreg = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=3000, C=0.8)),
    ])
    rf = RandomForestClassifier(
        n_estimators=400, max_depth=9, min_samples_leaf=25,
        max_features="sqrt", random_state=SEED, n_jobs=-1,
    )
    xgb = XGBClassifier(
        objective="multi:softprob", num_class=3, n_estimators=350,
        max_depth=4, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9,
        reg_lambda=1.2, min_child_weight=3, tree_method="hist",
        random_state=SEED, n_jobs=-1, eval_metric="mlogloss",
    )
    return logreg, rf, xgb


def main() -> None:
    X, y = _load_train()
    n = len(y)
    split = int(n * 0.8)
    Xtr, ytr = X[:split], y[:split]
    Xva, yva = X[split:], y[split:]

    # ---- Draw model + Elo baseline ---------------------------------------
    draw_model = _fit_draw_model(Xtr, ytr)
    elo_val = evaluate_model(yva, elo_baseline_proba(Xva, draw_model))

    # ---- ML models --------------------------------------------------------
    logreg, rf, xgb = _build_models()
    logreg.fit(Xtr, ytr)
    rf.fit(Xtr, ytr)
    xgb.fit(Xtr, ytr)

    val_metrics = {
        "elo": elo_val,
        "logreg": evaluate_model(yva, logreg.predict_proba(Xva)),
        "rf": evaluate_model(yva, rf.predict_proba(Xva)),
        "xgb": evaluate_model(yva, xgb.predict_proba(Xva)),
    }

    # ---- Refit on ALL history for the final artifacts --------------------
    draw_model = _fit_draw_model(X, y)
    logreg, rf, xgb = _build_models()
    logreg.fit(X, y)
    rf.fit(X, y)
    xgb.fit(X, y)

    # ---- Feature importances ---------------------------------------------
    logreg_imp = np.mean(np.abs(logreg.named_steps["clf"].coef_), axis=0)
    # Elo baseline: correlation of each feature with a home-advantage signal.
    home_signal = (y == 0).astype(float) - (y == 2).astype(float)
    elo_imp = np.array([
        abs(np.corrcoef(X[:, i], home_signal)[0, 1]) if np.std(X[:, i]) > 1e-9 else 0.0
        for i in range(X.shape[1])
    ])
    importances = {
        "elo": normalize_importance(elo_imp, FEATURE_ORDER),
        "logreg": normalize_importance(logreg_imp, FEATURE_ORDER),
        "rf": normalize_importance(rf.feature_importances_, FEATURE_ORDER),
        "xgb": normalize_importance(xgb.feature_importances_, FEATURE_ORDER),
    }

    joblib.dump(draw_model, os.path.join(MODELS_DIR, "elo_draw.joblib"))
    joblib.dump(logreg, os.path.join(MODELS_DIR, "logreg.joblib"))
    joblib.dump(rf, os.path.join(MODELS_DIR, "rf.joblib"))
    joblib.dump(xgb, os.path.join(MODELS_DIR, "xgb.joblib"))

    meta = {
        "feature_order": FEATURE_ORDER,
        "importances": importances,
        "validation": val_metrics,
        "trainRows": int(n),
        "feature_stats": {
            FEATURE_ORDER[i]: {"mean": round(float(X[:, i].mean()), 4),
                               "std": round(float(X[:, i].std() + 1e-9), 4)}
            for i in range(X.shape[1])
        },
        "updated": now_iso(),
    }
    with open(os.path.join(MODELS_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("[train] validation accuracy:",
          {k: v["accuracy"] for k, v in val_metrics.items()})
    print("[train] validation logloss:",
          {k: v["logLoss"] for k, v in val_metrics.items()})


if __name__ == "__main__":
    main()
