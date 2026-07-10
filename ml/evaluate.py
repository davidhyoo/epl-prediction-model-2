"""
evaluate.py  —  Stage 6: backtest, self-improvement & final assembly
====================================================================
Scores every model against the COMPLETED matches only (no leakage), then:

  * derives ensemble weights ∝ 1 / log-loss  (the self-improvement loop),
  * assembles the weighted-ensemble prediction for every match,
  * re-ranks the models and flags any that under-perform,
  * writes the final frontend datasets: matches.json, models.json,
    bracket.json and summary.json.
"""
from __future__ import annotations

import os

import numpy as np

from common import (
    PROCESSED_DIR, OUTPUTS_DIR, MODELS_DIR, PUBLIC_DATA_DIR, FEATURE_ORDER,
    read_json, publish, now_iso, CUTOFF, TOURNAMENT, HOST,
)
from modeling import evaluate_model, normalize_importance

MODEL_META = {
    "elo": ("Elo Baseline", "baseline",
            "Analytic two-stage Elo with a fitted draw model.",
            "Transparent, robust benchmark that is hard to beat."),
    "logreg": ("Logistic Regression", "linear",
               "Multinomial logistic regression on standardised features.",
               "Interpretable coefficients; well-calibrated probabilities."),
    "rf": ("Random Forest", "tree",
           "400 bagged decision trees on the engineered features.",
           "Captures non-linear interactions without much tuning."),
    "xgb": ("XGBoost", "boosting",
            "Gradient-boosted trees (350 rounds, depth 4).",
            "Usually the strongest single learner on tabular data."),
    "ensemble": ("Weighted Ensemble", "ensemble",
                 "Performance-weighted blend of all four base models.",
                 "Combines complementary models; weights adapt to results."),
}

STAGE_LABEL = {
    "group": "Group Stage", "round-of-32": "Round of 32", "round-of-16": "Round of 16",
    "quarter-final": "Quarter-final", "semi-final": "Semi-final",
    "third-place": "Third-place Play-off", "final": "Final",
}
STAGE_ROUND = {"group": 0, "round-of-32": 1, "round-of-16": 2, "quarter-final": 3,
               "semi-final": 4, "third-place": 5, "final": 6}
PROJECTED_STAGES = {"round-of-16", "quarter-final", "semi-final", "third-place", "final"}


def _model_prediction(model_id: str, prob_vec, accuracy: float,
                      home_code, away_code, home_name, away_name) -> dict:
    p = np.asarray(prob_vec, dtype=float)
    p = p / p.sum()
    arg = int(p.argmax())
    outcome = ["home", "draw", "away"][arg]
    if arg == 0:
        winner, winner_code = home_name, home_code
    elif arg == 2:
        winner, winner_code = away_name, away_code
    else:
        winner, winner_code = "Draw", None
    name, _type, _desc, _str = MODEL_META[model_id]
    return {
        "model": model_id, "modelName": name,
        "probs": {"home": round(float(p[0]), 4), "draw": round(float(p[1]), 4),
                  "away": round(float(p[2]), 4)},
        "predictedOutcome": outcome, "winner": winner, "winnerCode": winner_code,
        "confidence": round(float(p.max()), 4), "accuracy": round(accuracy, 4),
    }


def main() -> None:
    preds = read_json(os.path.join(OUTPUTS_DIR, "predictions.json"))["matches"]
    wc = read_json(os.path.join(PROCESSED_DIR, "wc_matches.json"))
    teams = read_json(os.path.join(PROCESSED_DIR, "teams.json"))
    meta = read_json(os.path.join(MODELS_DIR, "meta.json"))
    teams_pub = read_json(os.path.join(PUBLIC_DATA_DIR, "teams.json"))
    players_pub = read_json(os.path.join(PUBLIC_DATA_DIR, "players.json"))

    wc_by_id = {m["id"]: m for m in wc}
    ref = {t["code"]: {"code": t["code"], "iso2": t["iso2"], "name": t["name"],
                       "colors": t["colors"]} for t in teams}
    name_by_code = {t["code"]: t["name"] for t in teams}

    base_models = ["elo", "logreg", "rf", "xgb"]

    # ---- Gather probability matrices, split completed vs all -------------
    P = {mdl: np.array([row["probs"][mdl] for row in preds]) for mdl in base_models}
    completed_mask = np.array([row["status"] == "completed" for row in preds])
    y_all = np.array([row["y"] if row["y"] is not None else -1 for row in preds])
    y_comp = y_all[completed_mask]

    # ---- Score base models on completed matches --------------------------
    base_metrics = {}
    for mdl in base_models:
        base_metrics[mdl] = evaluate_model(y_comp, P[mdl][completed_mask])

    # ---- Self-improvement: ensemble weights ∝ 1 / log-loss ---------------
    lls = np.array([base_metrics[m]["logLoss"] for m in base_models])
    inv = 1.0 / np.clip(lls, 1e-6, None)
    weights = inv / inv.sum()
    weight_by_model = {m: float(w) for m, w in zip(base_models, weights)}

    # ---- Assemble weighted ensemble for ALL matches ----------------------
    stacked = np.stack([P[m] for m in base_models], axis=0)      # (4, n, 3)
    P_ens = np.tensordot(weights, stacked, axes=(0, 0))
    P_ens = P_ens / P_ens.sum(axis=1, keepdims=True)
    ens_metrics = evaluate_model(y_comp, P_ens[completed_mask])

    all_metrics = {**base_metrics, "ensemble": ens_metrics}
    model_ids = base_models + ["ensemble"]
    accuracy_by_model = {m: all_metrics[m]["accuracy"] for m in model_ids}

    # ---- Rank models (by log-loss asc) + underperformance note -----------
    ranking = sorted(model_ids, key=lambda m: all_metrics[m]["logLoss"])
    rank_by_model = {m: i + 1 for i, m in enumerate(ranking)}
    worst = ranking[-1]

    ens_importance = normalize_importance(
        np.array([np.mean([next(it["importance"] for it in meta["importances"][mm]
                                if it["feature"] == f) for mm in base_models])
                  for f in FEATURE_ORDER]), FEATURE_ORDER)
    importance_by_model = {**meta["importances"], "ensemble": ens_importance}

    # ---- models.json ------------------------------------------------------
    models_out = []
    for mdl in model_ids:
        name, mtype, desc, strengths = MODEL_META[mdl]
        m = all_metrics[mdl]
        note = None
        if mdl == worst and mdl != "ensemble":
            note = "Highest log-loss on the current backtest — down-weighted in the ensemble."
        models_out.append({
            "id": mdl, "name": name, "type": mtype, "description": desc,
            "accuracy": m["accuracy"], "logLoss": m["logLoss"], "brier": m["brier"],
            "gamesEvaluated": m["gamesEvaluated"], "avgConfidence": m["avgConfidence"],
            "ece": m["ece"], "weight": round(weight_by_model.get(mdl, 1.0), 4),
            "rank": rank_by_model[mdl], "lastUpdated": now_iso(),
            "calibration": m["calibration"], "featureImportance": importance_by_model[mdl],
            "strengths": strengths, "note": note,
        })
    models_out.sort(key=lambda x: x["rank"])
    publish("models.json", models_out)

    # ---- matches.json -----------------------------------------------------
    matches_out = []
    for i, row in enumerate(preds):
        wm = wc_by_id[row["id"]]
        home_code, away_code = row["home"], row["away"]
        hn, an = name_by_code[home_code], name_by_code[away_code]
        completed = wm["status"] == "completed"

        model_preds = []
        for mdl in base_models:
            model_preds.append(_model_prediction(mdl, P[mdl][i], accuracy_by_model[mdl],
                                                  home_code, away_code, hn, an))
        ensemble_pred = _model_prediction("ensemble", P_ens[i], accuracy_by_model["ensemble"],
                                          home_code, away_code, hn, an)
        model_preds.append(ensemble_pred)

        predicted_outcome = ensemble_pred["predictedOutcome"]
        actual_outcome = ["home", "draw", "away"][wm["outcome"]] if completed else None
        correct = (predicted_outcome == actual_outcome) if completed else None

        matches_out.append({
            "id": row["id"], "stage": wm["stage"], "stageLabel": STAGE_LABEL[wm["stage"]],
            "group": wm.get("group"), "round": STAGE_ROUND[wm["stage"]],
            "datetime": wm["date"], "venue": wm["venue"], "city": wm["city"],
            "status": wm["status"],
            "home": ref[home_code], "away": ref[away_code],
            "score": {"home": wm["gh"], "away": wm["ga"]} if completed else None,
            "penalties": ({"home": wm["pens"][0], "away": wm["pens"][1]}
                          if (completed and wm.get("pens")) else None),
            "actualOutcome": actual_outcome,
            "ensemble": ensemble_pred, "models": model_preds, "factors": row["factors"],
            "predictedOutcome": predicted_outcome, "correct": correct,
            "projectedMatchup": wm["stage"] in PROJECTED_STAGES,
        })
    publish("matches.json", matches_out)

    # ---- bracket.json -----------------------------------------------------
    build_bracket(preds, wc_by_id, P_ens, {row["id"]: i for i, row in enumerate(preds)})

    # ---- summary.json -----------------------------------------------------
    completed_n = int(completed_mask.sum())
    upcoming_n = int((~completed_mask).sum())
    teams_sorted = sorted(teams_pub, key=lambda t: -t["championProb"])
    contenders = [{"code": t["code"], "name": t["name"], "iso2": t["iso2"],
                   "prob": t["championProb"]} for t in teams_sorted[:6]]

    upcoming_idx = [i for i, row in enumerate(preds) if row["status"] != "completed"]
    hi_match = max(upcoming_idx, key=lambda i: P_ens[i].max()) if upcoming_idx else 0
    best_model = ranking[0]

    summary = {
        "tournament": TOURNAMENT, "host": HOST,
        "asOf": CUTOFF.isoformat(), "cutoff": CUTOFF.isoformat(),
        "generatedAt": now_iso(),
        "totalMatches": len(preds), "matchesCompleted": completed_n,
        "matchesUpcoming": upcoming_n, "matchesLive": 0,
        "teamCount": len(teams_pub), "playerCount": len(players_pub),
        "modelCount": len(model_ids), "featureCount": len(FEATURE_ORDER),
        "trainingMatches": meta["trainRows"],
        "topChampion": contenders[0], "topContenders": contenders,
        "highestConfidenceMatchId": preds[hi_match]["id"],
        "bestModel": {"id": best_model, "name": MODEL_META[best_model][0],
                      "accuracy": all_metrics[best_model]["accuracy"],
                      "logLoss": all_metrics[best_model]["logLoss"],
                      "brier": all_metrics[best_model]["brier"]},
        "ensembleAccuracy": ens_metrics["accuracy"],
        "dataMode": "generated",
    }
    publish("summary.json", summary)

    # ---- search.json (lightweight index for the command palette) ---------
    search = {
        "teams": [{"code": t["code"], "iso2": t["iso2"], "name": t["name"],
                   "group": t["group"], "championProb": t["championProb"]}
                  for t in teams_sorted],
        "players": [{"id": p["id"], "name": p["name"], "country": p["country"],
                     "countryCode": p["countryCode"], "iso2": p["iso2"],
                     "position": p["position"], "club": p["club"],
                     "rating": p["rating"]}
                    for p in sorted(players_pub, key=lambda p: -p["rating"])],
    }
    publish("search.json", search)

    print(f"[evaluate] weights={ {m: round(weight_by_model[m],3) for m in base_models} }")
    print(f"[evaluate] accuracy={ {m: all_metrics[m]['accuracy'] for m in model_ids} }")
    print(f"[evaluate] best={best_model} ensembleAcc={ens_metrics['accuracy']} "
          f"completed={completed_n}")


def build_bracket(preds, wc_by_id, P_ens, idx_by_id) -> None:
    rounds_order = ["round-of-32", "round-of-16", "quarter-final",
                    "semi-final", "third-place", "final"]
    knockout = [m for m in wc_by_id.values() if m["stage"] != "group"]
    rounds = []
    for stage in rounds_order:
        stage_matches = sorted([m for m in knockout if m["stage"] == stage],
                               key=lambda m: m["slot"])
        out = []
        projected = stage in PROJECTED_STAGES
        for m in stage_matches:
            i = idx_by_id[m["id"]]
            p = P_ens[i]
            p_home = p[0] + 0.5 * p[1]
            p_away = p[2] + 0.5 * p[1]
            s = p_home + p_away
            out.append({
                "id": m["id"], "stage": stage, "slot": m["slot"],
                "home": m["home"], "away": m["away"],
                "homeProjected": projected, "awayProjected": projected,
                "score": None, "penalties": None, "winner": None,
                "status": "upcoming",
                "homeProb": round(float(p_home / s), 4),
                "awayProb": round(float(p_away / s), 4),
            })
        rounds.append({"stage": stage, "label": STAGE_LABEL[stage], "matches": out})
    publish("bracket.json", {"rounds": rounds})


if __name__ == "__main__":
    main()
