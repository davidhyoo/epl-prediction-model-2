"""
club_predict.py  —  stage 5: match prediction + explanations
============================================================
Loads the trained models and scores **every** target-season match (played and
upcoming) with each model, producing home / draw / away probabilities. It also
builds a transparent per-match explanation (the top contributing factors) from
the logistic-regression coefficients, and a per-club "strength" snapshot used by
the rankings and club pages.

The result is returned in memory to the pipeline (evaluate then backtests the
model probabilities against real results, computes ensemble weights, and writes
the public JSON). Class order: 0 = home, 1 = draw, 2 = away.
"""
from __future__ import annotations

import os

import joblib
import numpy as np

import club_ingest as I
from club_features import (FEATURE_LABELS, FEATURE_ORDER, build_season_features,
                           build_training_matrix, outcome_label)
from club_modeling import elo_baseline_proba, ensemble_proba
from leagues import MODELS_DIR

ML_MODELS = ["logreg", "forest", "xgb"]


def _model_dir(league_id: str, season_id: str) -> str:
    return os.path.join(MODELS_DIR, f"{league_id}-{season_id}")


def load_models(league_id: str, season_id: str) -> dict:
    d = _model_dir(league_id, season_id)
    return {name: joblib.load(os.path.join(d, f"{name}.joblib"))
            for name in (*ML_MODELS, "draw")}


def _logreg_contributions(pipe, X: np.ndarray, pred: np.ndarray) -> list[list[dict]]:
    """Signed per-feature contribution to the *predicted* class for each row.

    Uses the standardised feature value × the class coefficient — an honest,
    inexpensive linear explanation (no SHAP dependency needed).
    """
    scaler = pipe.named_steps["scale"]
    clf = pipe.named_steps["clf"]
    Xs = scaler.transform(X)
    coefs = clf.coef_                       # (n_classes, n_features)
    out: list[list[dict]] = []
    for i in range(len(X)):
        c = pred[i]
        contrib = coefs[c] * Xs[i]          # (n_features,)
        order = np.argsort(-np.abs(contrib))
        feats = []
        for j in order[:5]:
            f = FEATURE_ORDER[j]
            feats.append({
                "feature": f,
                "label": FEATURE_LABELS.get(f, f),
                "value": round(float(X[i, j]), 3),
                "impact": round(float(contrib[j]), 4),
                "direction": "home" if contrib[j] > 0 else "away",
            })
        out.append(feats)
    return out


def _scale01(values: dict[str, float], invert: bool = False) -> dict[str, float]:
    if not values:
        return {}
    v = np.array(list(values.values()), dtype=float)
    lo, hi = float(v.min()), float(v.max())
    span = (hi - lo) or 1.0
    out = {}
    for k, x in values.items():
        s = (x - lo) / span
        out[k] = round(float(100.0 * (1 - s if invert else s)), 1)
    return out


def team_strength(eng, codes: list[str]) -> dict[str, dict]:
    """0–100 strength ratings within the current league field."""
    codes = [c for c in codes if not c.startswith("~")]
    elo = {c: eng._get_elo(c) for c in codes}
    gf = {c: eng._avg(eng.gf[c], 0.0) for c in codes}
    ga = {c: eng._avg(eng.ga[c], 0.0) for c in codes}
    ppg = {c: eng._ppg(c) for c in codes}

    overall = _scale01(elo)
    attack = _scale01(gf)
    defense = _scale01(ga, invert=True)   # fewer conceded = stronger
    form = _scale01(ppg)

    out = {}
    for c in codes:
        out[c] = {
            "elo": round(float(elo[c]), 1),
            "overall": overall.get(c, 50.0),
            "attack": attack.get(c, 50.0),
            "defense": defense.get(c, 50.0),
            "form": form.get(c, 50.0),
            "gfAvg": round(float(gf[c]), 3),
            "gaAvg": round(float(ga[c]), 3),
            "ppg": round(float(ppg[c]), 3),
        }
    return out


def predict_combo(league_id: str, season_id: str) -> dict:
    ing = I.main(league_id, season_id)
    corpus, data = ing["corpus"], ing["data"]
    models = load_models(league_id, season_id)

    # prime the engine on the corpus, then walk the season (records pre-match Elo)
    _, _, eng = build_training_matrix(corpus)
    X, ordered = build_season_features(eng, data["matches"])

    proba: dict[str, np.ndarray] = {}
    for name in ML_MODELS:
        proba[name] = models[name].predict_proba(X)
    proba["elo"] = elo_baseline_proba(X, models["draw"])

    # equal-weight ensemble as a sensible default (evaluate overrides with
    # inverse-log-loss weights once it has backtest metrics)
    default_w = np.ones(len(ML_MODELS) + 1)
    ens = ensemble_proba([proba[n] for n in (*ML_MODELS, "elo")], default_w)
    proba["ensemble"] = ens

    pred = ens.argmax(axis=1)
    contributions = _logreg_contributions(models["logreg"], X, pred)

    # market baseline probabilities where bookmaker odds exist (NaN otherwise)
    market = np.full((len(ordered), 3), np.nan)
    for i, m in enumerate(ordered):
        o = m.get("marketOdds")
        if o:
            market[i] = [o["home"], o["draw"], o["away"]]

    codes = [c for c in data["codes"] if not c.startswith("~")]
    strength = team_strength(eng, codes)

    # true labels for completed matches (evaluate uses these; leakage-free since
    # they are never fed back into features)
    y = np.array([outcome_label(m["homeGoals"], m["awayGoals"])
                  if m["status"] == "completed" else -1 for m in ordered])

    return {
        "league": league_id, "season": season_id,
        "ordered": ordered, "X": X, "y": y,
        "proba": proba, "market": market,
        "contributions": contributions,
        "strength": strength, "codes": codes, "engine": eng,
    }


if __name__ == "__main__":
    r = predict_combo("epl", "2025-26")
    n = len(r["ordered"])
    played = int((r["y"] >= 0).sum())
    print(f"epl 2025-26: {n} matches scored, {played} completed")
    # sanity: ensemble accuracy on completed games
    mask = r["y"] >= 0
    acc = float((r["proba"]["ensemble"][mask].argmax(1) == r["y"][mask]).mean())
    print(f"ensemble train-season accuracy (in-sample-free): {acc:.3f}")
