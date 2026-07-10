"""
modeling.py
===========
Shared modelling helpers used by train / predict / evaluate:

  * the analytic Elo-baseline probability model (home / draw / away)
  * ensemble blending
  * probabilistic metrics (accuracy, multiclass log-loss, Brier score)
  * calibration bins + Expected Calibration Error (ECE)

Class order is fixed everywhere: index 0 = home win, 1 = draw, 2 = away win.
"""
from __future__ import annotations

import numpy as np

from common import FEATURE_ORDER, HOME_ADV

HOME_IDX = FEATURE_ORDER.index("host_adv")
ELO_IDX = FEATURE_ORDER.index("elo_diff")
CLASSES = 3


def elo_effective_diff(X: np.ndarray) -> np.ndarray:
    """Elo difference including host advantage (home minus away)."""
    return X[:, ELO_IDX] + HOME_ADV * X[:, HOME_IDX]


def elo_baseline_proba(X: np.ndarray, draw_model) -> np.ndarray:
    """Two-stage Elo baseline: a draw model + the Elo win/loss split."""
    eff = elo_effective_diff(X)
    p_home_core = 1.0 / (1.0 + np.power(10.0, -eff / 400.0))
    draw_p = draw_model.predict_proba(np.abs(eff).reshape(-1, 1))[:, 1]
    home = (1.0 - draw_p) * p_home_core
    away = (1.0 - draw_p) * (1.0 - p_home_core)
    P = np.column_stack([home, draw_p, away])
    return P / P.sum(axis=1, keepdims=True)


def ensemble_proba(prob_list: list[np.ndarray], weights: np.ndarray) -> np.ndarray:
    """Weighted average of probability matrices, renormalised."""
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    stacked = np.stack(prob_list, axis=0)         # (n_models, n, 3)
    blended = np.tensordot(w, stacked, axes=(0, 0))
    return blended / blended.sum(axis=1, keepdims=True)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def accuracy(y: np.ndarray, P: np.ndarray) -> float:
    return float(np.mean(P.argmax(axis=1) == y))


def log_loss(y: np.ndarray, P: np.ndarray, eps: float = 1e-15) -> float:
    P = np.clip(P, eps, 1 - eps)
    return float(-np.mean(np.log(P[np.arange(len(y)), y])))


def brier(y: np.ndarray, P: np.ndarray) -> float:
    onehot = np.zeros_like(P)
    onehot[np.arange(len(y)), y] = 1.0
    return float(np.mean(np.sum((P - onehot) ** 2, axis=1)))


def calibration(y: np.ndarray, P: np.ndarray, n_bins: int = 10) -> tuple[list, float]:
    """Reliability bins based on the confidence (max prob) of the predicted class."""
    conf = P.max(axis=1)
    pred = P.argmax(axis=1)
    correct = (pred == y).astype(float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    out, ece = [], 0.0
    n = len(y)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (conf > lo) & (conf <= hi) if i > 0 else (conf >= lo) & (conf <= hi)
        cnt = int(mask.sum())
        if cnt == 0:
            continue
        avg_conf = float(conf[mask].mean())
        obs = float(correct[mask].mean())
        out.append({"predicted": round(avg_conf, 4),
                    "observed": round(obs, 4), "count": cnt})
        ece += abs(avg_conf - obs) * cnt / n
    return out, float(ece)


def evaluate_model(y: np.ndarray, P: np.ndarray) -> dict:
    cal, ece = calibration(y, P)
    return {
        "accuracy": round(accuracy(y, P), 4),
        "logLoss": round(log_loss(y, P), 4),
        "brier": round(brier(y, P), 4),
        "avgConfidence": round(float(P.max(axis=1).mean()), 4),
        "ece": round(ece, 4),
        "calibration": cal,
        "gamesEvaluated": int(len(y)),
    }


def normalize_importance(values: np.ndarray, feature_order: list[str]) -> list[dict]:
    from common import FEATURE_LABELS
    v = np.abs(np.asarray(values, dtype=float))
    if v.sum() == 0:
        v = np.ones_like(v)
    v = v / v.sum()
    order = np.argsort(-v)
    return [{"feature": feature_order[i],
             "label": FEATURE_LABELS.get(feature_order[i], feature_order[i]),
             "importance": round(float(v[i]), 4)} for i in order]
