"""
club_evaluate.py  —  stage 8: backtest, blend, assemble & publish
=================================================================
The final analytics stage. For each (league, season) it:

  1. **Backtests** every model against the season's completed matches (accuracy,
     multiclass log-loss, Brier score, calibration/ECE) — leakage-free, because
     the models never trained on this season.
  2. Computes **ensemble weights ∝ 1/log-loss** (better models earn more say) and
     re-blends the per-match ensemble with those weights. If no match has been
     played yet (the upcoming deliverable season) it falls back to equal weights.
  3. Builds the **standings** table (real results) and the **Monte-Carlo season
     odds** (title / UCL / Europa / relegation / finishing-position distribution).
  4. Merges the **player roster + real goal stats** and derives club **strengths**,
     **rankings** and per-club **detail**.
  5. Writes namespaced public JSON under ``public/data/{league}/{season}/`` plus a
     top-level ``public/data/index.json`` describing the available datasets.

Everything is deterministic (fixed seed) and offline (reads only the cached
sources + trained models), so a refresh reproduces byte-stable output.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np

import club_players as P
import club_simulate as SIM
import club_fpl as FPL
from club_features import outcome_label
from club_modeling import (ensemble_proba, evaluate_model, inverse_logloss_weights,
                           log_loss)
from club_predict import ML_MODELS, predict_combo
from leagues import (COMBOS, LEAGUES, PUBLIC_DATA_DIR, SEASONS, SOURCE_DIR,
                     club, public_dir)

# league bracket sizes (rows counted from the top / bottom of the table)
BRACKETS = {
    "epl": {"ucl": 5, "europa": 7, "releg": 3},      # 5th earns UCL via coefficient
    "laliga": {"ucl": 5, "europa": 7, "releg": 3},
}
MODEL_LABELS = {
    "logreg": "Logistic Regression", "forest": "Random Forest",
    "xgb": "XGBoost", "elo": "Elo Baseline", "market": "Market Baseline",
    "ensemble": "Ensemble",
}
MODEL_BLURB = {
    "logreg": "Multinomial logistic regression over the engineered feature set.",
    "forest": "Bootstrapped decision-tree ensemble capturing non-linear splits.",
    "xgb": "Gradient-boosted trees — the usual football-modelling workhorse.",
    "elo": "Analytic World-Football-Elo model with a fitted draw component.",
    "market": "Closing bookmaker odds, de-margined — the benchmark to beat.",
    "ensemble": "Inverse-log-loss weighted blend of the models above.",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_squads(league_id: str) -> dict:
    path = os.path.join(SOURCE_DIR, league_id, "squads_wikipedia.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("squads", {})


def _club_meta(league_id: str, code: str) -> dict:
    c = club(league_id, code)
    return {"code": c.code, "name": c.name, "short": c.short,
            "primary": c.primary, "secondary": c.secondary, "wiki": c.wiki}


# --------------------------------------------------------------------------- #
# Standings
# --------------------------------------------------------------------------- #
def _standings(league_id: str, codes: list[str], matches: list[dict],
               sim: dict) -> list[dict]:
    row = {c: {"code": c, "played": 0, "win": 0, "draw": 0, "loss": 0,
               "gf": 0, "ga": 0, "pts": 0, "form": []} for c in codes}
    for m in sorted(matches, key=lambda x: x.get("date") or ""):
        if m["status"] != "completed":
            continue
        h, a, hg, ag = m["home"], m["away"], m["homeGoals"], m["awayGoals"]
        if h not in row or a not in row:
            continue
        for side, gf, ga in ((h, hg, ag), (a, ag, hg)):
            r = row[side]
            r["played"] += 1; r["gf"] += gf; r["ga"] += ga
        if hg > ag:
            row[h]["win"] += 1; row[h]["pts"] += 3; row[h]["form"].append("W")
            row[a]["loss"] += 1; row[a]["form"].append("L")
        elif hg < ag:
            row[a]["win"] += 1; row[a]["pts"] += 3; row[a]["form"].append("W")
            row[h]["loss"] += 1; row[h]["form"].append("L")
        else:
            row[h]["draw"] += 1; row[a]["draw"] += 1
            row[h]["pts"] += 1; row[a]["pts"] += 1
            row[h]["form"].append("D"); row[a]["form"].append("D")

    rows = list(row.values())
    any_played = any(r["played"] for r in rows)
    for r in rows:
        r["gd"] = r["gf"] - r["ga"]
        r["form"] = r["form"][-5:]
        r["expectedPoints"] = sim.get(r["code"], {}).get("expectedPoints")
    if any_played:
        rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"], r["code"]))
    else:
        # pre-season: order by the model's projected points
        rows.sort(key=lambda r: -(r["expectedPoints"] or 0))
    for i, r in enumerate(rows):
        r["position"] = i + 1
    return rows


# --------------------------------------------------------------------------- #
# Matches (with predictions + explanations)
# --------------------------------------------------------------------------- #
def _match_records(league_id: str, pred: dict, weights: dict[str, float]) -> list[dict]:
    ordered = pred["ordered"]
    proba, market, contrib = pred["proba"], pred["market"], pred["contributions"]
    w = np.array([weights[m] for m in ML_MODELS] + [weights["elo"]])
    ens = ensemble_proba([proba[m] for m in (*ML_MODELS, "elo")], w)

    out = []
    for i, m in enumerate(ordered):
        models = {}
        for name in (*ML_MODELS, "elo"):
            p = proba[name][i]
            models[name] = {"home": round(float(p[0]), 4),
                            "draw": round(float(p[1]), 4),
                            "away": round(float(p[2]), 4)}
        if not np.isnan(market[i]).any():
            mk = market[i]
            models["market"] = {"home": round(float(mk[0]), 4),
                                "draw": round(float(mk[1]), 4),
                                "away": round(float(mk[2]), 4)}
        e = ens[i]
        ens_probs = {"home": round(float(e[0]), 4),
                     "draw": round(float(e[1]), 4),
                     "away": round(float(e[2]), 4)}
        pred_idx = int(e.argmax())
        rec = {
            "id": m["id"], "round": m["round"],
            "date": m.get("date"), "datetime": m.get("datetime"),
            "status": m["status"],
            "home": _club_meta(league_id, m["home"]),
            "away": _club_meta(league_id, m["away"]),
            "homeGoals": m.get("homeGoals"), "awayGoals": m.get("awayGoals"),
            "eloHome": m.get("_elo_home"), "eloAway": m.get("_elo_away"),
            "prediction": {
                "ensemble": ens_probs,
                "models": models,
                "predicted": ["home", "draw", "away"][pred_idx],
                "confidence": round(float(e.max()), 4),
                "topFactors": contrib[i],
            },
            "scorers": _clean_scorers(league_id, m.get("scorers") or []),
            "matchStats": m.get("matchStats"),
            "marketOdds": m.get("marketOdds"),
        }
        if m["status"] == "completed":
            actual = ["home", "draw", "away"][outcome_label(m["homeGoals"], m["awayGoals"])]
            rec["actual"] = actual
            rec["predictionCorrect"] = (actual == rec["prediction"]["predicted"])
        out.append(rec)
    return out


def _clean_scorers(league_id: str, scorers: list[dict]) -> list[dict]:
    out = []
    for s in scorers:
        out.append({
            "player": s.get("player", "").title(),
            "team": s.get("scorerTeam"),
            "minute": s.get("minuteLabel"),
            "penalty": s.get("penalty", False),
            "ownGoal": s.get("ownGoal", False),
        })
    return out


# --------------------------------------------------------------------------- #
# Models leaderboard (backtest)
# --------------------------------------------------------------------------- #
def _model_leaderboard(pred: dict, weights: dict) -> tuple[list[dict], dict]:
    y = pred["y"]
    mask = y >= 0
    yv = y[mask]
    board = []
    for name in (*ML_MODELS, "elo"):
        entry = {"id": name, "name": MODEL_LABELS[name], "blurb": MODEL_BLURB[name],
                 "weight": round(float(weights.get(name, 0.0)), 4)}
        if mask.sum() > 0:
            entry.update(evaluate_model(yv, pred["proba"][name][mask]))
        else:
            entry.update({"accuracy": None, "logLoss": None, "brier": None,
                          "avgConfidence": None, "ece": None, "calibration": [],
                          "gamesEvaluated": 0})
        board.append(entry)

    # market baseline only where odds exist
    market = pred["market"]
    mk_mask = mask & ~np.isnan(market).any(axis=1)
    mk_entry = {"id": "market", "name": MODEL_LABELS["market"],
                "blurb": MODEL_BLURB["market"], "weight": 0.0}
    if mk_mask.sum() > 0:
        mk_entry.update(evaluate_model(y[mk_mask], market[mk_mask]))
    else:
        mk_entry.update({"accuracy": None, "logLoss": None, "brier": None,
                         "avgConfidence": None, "ece": None, "calibration": [],
                         "gamesEvaluated": 0})
    board.append(mk_entry)

    # ensemble row
    w = np.array([weights[m] for m in ML_MODELS] + [weights["elo"]])
    ens = ensemble_proba([pred["proba"][m] for m in (*ML_MODELS, "elo")], w)
    ens_entry = {"id": "ensemble", "name": MODEL_LABELS["ensemble"],
                 "blurb": MODEL_BLURB["ensemble"], "weight": 1.0}
    if mask.sum() > 0:
        ens_entry.update(evaluate_model(yv, ens[mask]))
    else:
        ens_entry.update({"accuracy": None, "logLoss": None, "brier": None,
                          "avgConfidence": None, "ece": None, "calibration": [],
                          "gamesEvaluated": 0})
    board.append(ens_entry)

    scored = [b for b in board if b.get("accuracy") is not None]
    scored.sort(key=lambda b: (b["logLoss"], -b["accuracy"]))
    ranked = scored + [b for b in board if b.get("accuracy") is None]
    for i, b in enumerate(ranked):
        b["rank"] = i + 1 if b.get("accuracy") is not None else None
    return ranked, {"evaluated": int(mask.sum())}


def _compute_weights(pred: dict) -> dict[str, float]:
    y = pred["y"]; mask = y >= 0
    names = [*ML_MODELS, "elo"]
    if mask.sum() < 10:
        return {n: 1.0 / len(names) for n in names}
    ll = {n: log_loss(y[mask], pred["proba"][n][mask]) for n in names}
    return inverse_logloss_weights(ll)


# --------------------------------------------------------------------------- #
# Rankings + clubs
# --------------------------------------------------------------------------- #
def _rankings(codes, strength, sim, standings, squad_rating) -> dict:
    def view(metric_fn, reverse=True):
        rows = [{"code": c, "value": round(float(metric_fn(c)), 2)} for c in codes]
        rows.sort(key=lambda r: -r["value"] if reverse else r["value"])
        for i, r in enumerate(rows):
            r["rank"] = i + 1
        return rows

    st_by_code = {r["code"]: r for r in standings}
    return {
        "title": [{"code": c, "value": round(sim.get(c, {}).get("title", 0) * 100, 2)}
                  for c in sorted(codes, key=lambda c: -sim.get(c, {}).get("title", 0))],
        "strength": view(lambda c: strength.get(c, {}).get("overall", 50)),
        "form": view(lambda c: strength.get(c, {}).get("form", 50)),
        "attack": view(lambda c: strength.get(c, {}).get("attack", 50)),
        "defense": view(lambda c: strength.get(c, {}).get("defense", 50)),
        "squad": view(lambda c: squad_rating.get(c, 50)),
        "elo": view(lambda c: strength.get(c, {}).get("elo", 1500)),
        "momentum": view(lambda c: st_by_code.get(c, {}).get("pts", 0)),
    }


def _clubs(league_id, codes, standings, strength, sim, players, matches) -> list[dict]:
    st_by_code = {r["code"]: r for r in standings}
    squad_by_club: dict[str, list] = {}
    for p in players:
        squad_by_club.setdefault(p["club"], []).append(p)

    fixtures_by_club: dict[str, dict] = {c: {"played": [], "upcoming": []} for c in codes}
    for m in matches:
        for side in (m["home"]["code"], m["away"]["code"]):
            if side in fixtures_by_club:
                bucket = "played" if m["status"] == "completed" else "upcoming"
                fixtures_by_club[side][bucket].append(m["id"])

    out = []
    for c in codes:
        st = strength.get(c, {})
        squad = sorted(squad_by_club.get(c, []), key=lambda p: -p["rating"])
        strengths, weaknesses = _swot(st)
        out.append({
            **_club_meta(league_id, c),
            "standing": st_by_code.get(c),
            "strength": st,
            "odds": sim.get(c, {}),
            "keyPlayers": [p["id"] for p in squad[:5]],
            "squadSize": len(squad),
            "playedMatches": fixtures_by_club[c]["played"],
            "upcomingMatches": fixtures_by_club[c]["upcoming"],
            "strengthsText": strengths, "weaknessesText": weaknesses,
        })
    return out


def _swot(st: dict) -> tuple[list[str], list[str]]:
    strengths, weaknesses = [], []
    labels = [("attack", "Attacking output", "Blunt in the final third"),
              ("defense", "Defensive solidity", "Leaky at the back"),
              ("form", "In-form", "Poor recent form"),
              ("overall", "Squad quality", "Thin squad depth")]
    for key, pos, neg in labels:
        v = st.get(key, 50)
        if v >= 66:
            strengths.append(pos)
        elif v <= 34:
            weaknesses.append(neg)
    return strengths or ["Balanced side"], weaknesses or ["Few obvious weaknesses"]


# --------------------------------------------------------------------------- #
# Assemble one combo
# --------------------------------------------------------------------------- #
def build_combo(league_id: str, season_id: str) -> dict:
    pred = predict_combo(league_id, season_id)
    codes = pred["codes"]
    strength = pred["strength"]
    matches_raw = pred["ordered"]

    br = BRACKETS[league_id]
    completed = [m for m in matches_raw if m["status"] == "completed"]
    remaining = [m for m in matches_raw if m["status"] != "completed"]
    sim = SIM.simulate(codes, {c: strength[c]["elo"] for c in codes},
                       completed, remaining,
                       ucl=br["ucl"], europa=br["europa"], releg=br["releg"])

    standings = _standings(league_id, codes, matches_raw, sim)
    weights = _compute_weights(pred)
    matches = _match_records(league_id, pred, weights)
    board, board_meta = _model_leaderboard(pred, weights)

    squads = _load_squads(league_id)
    squads = {k: v for k, v in squads.items() if k in codes}
    pdata = P.build_players(league_id, season_id, squads, strength, matches_raw)
    players = pdata["players"]
    # Enrich with real assists / minutes / cards (EPL only; La Liga has no free
    # key-less per-player feed, so its stats stay null). No-op if the cache is
    # missing or the league is unsupported — never fabricates a number.
    cov = FPL.enrich_players(league_id, season_id, players, played=len(completed))
    if cov["matched"]:
        print(f"  [fpl] {league_id} {season_id}: assists/minutes for "
              f"{cov['matched']}/{cov['total']} players "
              f"({cov['assists']} with 1+ assist)")
    squad_rating = {}
    for c in codes:
        rr = [p["rating"] for p in players if p["club"] == c]
        squad_rating[c] = round(float(np.mean(sorted(rr, reverse=True)[:16])), 1) if rr else 50.0

    rankings = _rankings(codes, strength, sim, standings, squad_rating)
    clubs = _clubs(league_id, codes, standings, strength, sim, players, matches)

    # Title-race timeline: how each club's championship probability evolves
    # matchday by matchday (empty until the season has completed matches).
    race = _title_race(league_id, codes, matches_raw, sim)

    # champion = highest title probability
    champ = max(codes, key=lambda c: sim.get(c, {}).get("title", 0)) if codes else None
    played_n = len(completed)
    upcoming = [m for m in matches if m["status"] != "completed"]
    best_model = next((b for b in board if b.get("rank") == 1), None)
    top_scorer = next((p for p in sorted(players, key=lambda p: -p["goals"])
                       if p["goals"] > 0), None)

    lg = LEAGUES[league_id]; sn = SEASONS[season_id]
    summary = {
        "league": {"id": lg.id, "name": lg.name, "short": lg.short,
                   "country": lg.country, "iso2": lg.iso2, "accent": lg.accent},
        "season": {"id": sn.id, "label": sn.label, "role": sn.role},
        "lastUpdated": _now_iso(),
        "totalMatches": len(matches), "played": played_n,
        "upcoming": len(upcoming), "clubs": len(codes),
        "champion": {"code": champ, "name": club(league_id, champ).name,
                     "probability": round(sim.get(champ, {}).get("title", 0) * 100, 1)}
        if champ else None,
        "topScorer": {"id": top_scorer["id"], "name": top_scorer["name"],
                      "club": top_scorer["club"], "goals": top_scorer["goals"]}
        if top_scorer else None,
        "bestModel": {"id": best_model["id"], "name": best_model["name"],
                      "accuracy": best_model.get("accuracy")} if best_model else None,
        "highestConfidence": _highest_conf(upcoming),
    }
    return {
        "summary": summary, "standings": standings, "matches": matches,
        "models": {"leaderboard": board, "meta": board_meta,
                   "weights": {k: round(v, 4) for k, v in weights.items()}},
        "clubs": clubs, "players": players, "rankings": rankings,
        "topScorers": pdata["topScorers"], "race": race,
    }


def _title_race(league_id: str, codes: list[str], matches_raw: list[dict],
                sim: dict) -> dict:
    """Assemble the publishable title-race timeline (see club_simulate)."""
    timeline = SIM.title_race_timeline(codes, matches_raw)
    series = timeline["series"]

    def final_p(c: str) -> float:
        vals = series.get(c) or []
        return vals[-1] if vals else float(sim.get(c, {}).get("title", 0.0))

    def peak_p(c: str) -> float:
        vals = series.get(c) or []
        return max(vals) if vals else float(sim.get(c, {}).get("title", 0.0))

    # order by peak probability so the genuine title contenders (not the
    # alphabetical also-rans) get the highlighted colours + legend slots
    ordered_codes = sorted(codes, key=lambda c: (-peak_p(c), -final_p(c)))
    club_rows = []
    for c in ordered_codes:
        cm = _club_meta(league_id, c)
        club_rows.append({"code": cm["code"], "short": cm["short"],
                          "name": cm["name"], "primary": cm["primary"],
                          "secondary": cm["secondary"],
                          "peak": round(peak_p(c) * 100, 2),
                          "final": round(final_p(c) * 100, 2)})
    return {
        "checkpoints": timeline["checkpoints"],
        "playedAt": timeline["playedAt"],
        "maxRound": timeline["maxRound"],
        "lastCompletedRound": timeline["lastCompletedRound"],
        "clubs": club_rows,
        "series": {c: [round(p * 100, 2) for p in series.get(c, [])] for c in codes},
    }


def _highest_conf(upcoming: list[dict]) -> dict | None:
    if not upcoming:
        return None
    best = max(upcoming, key=lambda m: m["prediction"]["confidence"])
    return {"id": best["id"], "home": best["home"]["name"], "away": best["away"]["name"],
            "predicted": best["prediction"]["predicted"],
            "confidence": round(best["prediction"]["confidence"] * 100, 1)}


# --------------------------------------------------------------------------- #
# Publish
# --------------------------------------------------------------------------- #
def _write(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))


def publish_combo(league_id: str, season_id: str) -> dict:
    data = build_combo(league_id, season_id)
    d = public_dir(league_id, season_id)
    _write(os.path.join(d, "summary.json"), data["summary"])
    _write(os.path.join(d, "standings.json"), data["standings"])
    _write(os.path.join(d, "matches.json"), data["matches"])
    _write(os.path.join(d, "models.json"), data["models"])
    _write(os.path.join(d, "clubs.json"), data["clubs"])
    _write(os.path.join(d, "players.json"),
           {"players": data["players"], "topScorers": data["topScorers"]})
    _write(os.path.join(d, "rankings.json"), data["rankings"])
    _write(os.path.join(d, "race.json"), data["race"])
    s = data["summary"]
    print(f"  [publish] {league_id} {season_id}: {s['played']}/{s['totalMatches']} played, "
          f"{len(data['players'])} players, champion "
          f"{s['champion']['code'] if s['champion'] else '—'} "
          f"({s['champion']['probability'] if s['champion'] else 0}%)")
    return {"league": league_id, "season": season_id,
            "played": s["played"], "players": len(data["players"])}


def write_index(results: list[dict]) -> None:
    from leagues import DEFAULT_LEAGUE, DEFAULT_SEASON
    idx = {
        "generatedAt": _now_iso(),
        "default": {"league": DEFAULT_LEAGUE, "season": DEFAULT_SEASON},
        "leagues": [
            {"id": lg.id, "name": lg.name, "short": lg.short, "country": lg.country,
             "iso2": lg.iso2, "accent": lg.accent,
             "seasons": [{"id": sn.id, "label": sn.label, "role": sn.role}
                         for sn in SEASONS.values()]}
            for lg in LEAGUES.values()
        ],
        "datasets": results,
    }
    _write(os.path.join(PUBLIC_DATA_DIR, "index.json"), idx)


def main(combos=None) -> None:
    combos = combos or COMBOS
    results = []
    for lg, sn in combos:
        results.append(publish_combo(lg, sn))
    write_index(results)
    print(f"[evaluate] published {len(results)} datasets -> {PUBLIC_DATA_DIR}")


if __name__ == "__main__":
    main()
