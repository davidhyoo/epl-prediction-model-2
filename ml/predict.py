"""
predict.py  —  Stage 5: prediction generation
==============================================
Loads the trained models and generates, for every 2026 World Cup match, the
per-model win/draw/loss probabilities plus transparent "top contributing
factors" for the explanation modal. It also:

  * runs a vectorised Monte-Carlo championship simulation (20k tournaments)
    for title odds & round-by-round advancement probabilities,
  * derives team strength / form / momentum metrics,
  * allocates realistic per-player tournament statistics,
  * builds the countries, players, rankings and methodology datasets.

Match-level ensemble assembly, model scoring and the summary/bracket live in
evaluate.py (the self-improvement loop). This step writes the leakage-free raw
predictions to ml/outputs/predictions.json.
"""
from __future__ import annotations

import os

import numpy as np
import joblib

from common import (
    PROCESSED_DIR, OUTPUTS_DIR, MODELS_DIR, FEATURE_ORDER, FEATURE_LABELS,
    read_json, write_json_pretty, publish, now_iso, scale_0_100, clamp, rng,
    load_teams, TOURNAMENT, HOST, CUTOFF, HOME_ADV,
)
from modeling import elo_baseline_proba
from tournament import simulate_knockouts

N_SIMS = 20000
N_SIMS_HISTORY = 6000
CLASS_NAMES = ["home", "draw", "away"]


# --------------------------------------------------------------------------- #
# Model loading + per-match probabilities
# --------------------------------------------------------------------------- #
def load_models():
    return {
        "draw": joblib.load(os.path.join(MODELS_DIR, "elo_draw.joblib")),
        "logreg": joblib.load(os.path.join(MODELS_DIR, "logreg.joblib")),
        "rf": joblib.load(os.path.join(MODELS_DIR, "rf.joblib")),
        "xgb": joblib.load(os.path.join(MODELS_DIR, "xgb.joblib")),
    }


def per_model_probs(models, X: np.ndarray) -> dict:
    return {
        "elo": elo_baseline_proba(X, models["draw"]),
        "logreg": models["logreg"].predict_proba(X),
        "rf": models["rf"].predict_proba(X),
        "xgb": models["xgb"].predict_proba(X),
    }


# --------------------------------------------------------------------------- #
# Explanation factors (transparent, importance-weighted feature contributions)
# --------------------------------------------------------------------------- #
def build_factors(feats: dict, avg_importance: dict, stats: dict,
                  home_name: str, away_name: str) -> list[dict]:
    contribs = []
    for f in FEATURE_ORDER:
        val = feats[f]
        std = stats[f]["std"]
        z = val / std if std > 1e-9 else 0.0
        mag = avg_importance.get(f, 0.0) * abs(z)
        if f == "stage_knockout":
            favors = "neutral"
        elif val > 0:
            favors = "home"
        elif val < 0:
            favors = "away"
        else:
            favors = "neutral"
        fav_name = home_name if favors == "home" else away_name
        contribs.append((mag, f, val, favors, fav_name))

    contribs.sort(key=lambda c: -c[0])
    top = [c for c in contribs if c[0] > 0][:5]
    total = sum(c[0] for c in top) or 1.0

    out = []
    for mag, f, val, favors, fav_name in top:
        out.append({
            "label": FEATURE_LABELS[f],
            "detail": _factor_detail(f, val, favors, fav_name),
            "favors": favors,
            "weight": round(mag / total, 3),
        })
    return out


def _factor_detail(f: str, val: float, favors: str, fav: str) -> str:
    a = abs(val)
    if favors == "neutral" and f != "stage_knockout":
        return "Evenly matched on this factor"
    if f == "elo_diff":
        return f"{fav} hold a {a:.0f}-point Elo rating edge"
    if f == "form_diff":
        return f"{fav} in better recent form (+{a:.2f} pts/game)"
    if f == "gf_diff":
        return f"{fav} scoring more freely (+{a:.2f} goals/game)"
    if f == "ga_diff":
        return f"{fav} more solid at the back ({a:.2f} fewer conceded/game)"
    if f == "xg_diff":
        return f"{fav} creating better chances (+{a:.2f} xG/game)"
    if f == "squad_diff":
        return f"{fav} carry the stronger overall squad rating"
    if f == "rest_diff":
        return f"{fav} enjoy a rest-and-recovery advantage"
    if f == "h2h_diff":
        return f"Head-to-head history favours {fav}"
    if f == "host_adv":
        return "Host-nation advantage (home support & familiarity)"
    if f == "stage_knockout":
        return "Knockout tie — no draws, margins tighten"
    return f"Advantage {fav}"


# --------------------------------------------------------------------------- #
# Championship Monte-Carlo
# --------------------------------------------------------------------------- #
def build_eff(team_dicts, elo_by_code, squad_by_code):
    idx = {t["code"]: i for i, t in enumerate(team_dicts)}
    eff = np.zeros(len(team_dicts))
    for t in team_dicts:
        base = elo_by_code.get(t["code"], t["elo0"])
        squad_bonus = (squad_by_code.get(t["code"], 50.0) - 50.0) * 1.6
        host_bonus = HOME_ADV * 0.55 if t.get("host") else 0.0
        eff[idx[t["code"]]] = base + squad_bonus + host_bonus
    return eff, idx


def run_championship(team_dicts, bracket_codes, elo_by_code, squad_by_code,
                     n_sims, generator):
    eff, idx = build_eff(team_dicts, elo_by_code, squad_by_code)
    positions_idx = np.array([idx[c] for c in bracket_codes], dtype=int)
    counts = simulate_knockouts(positions_idx, eff, n_sims, generator)
    inv = {i: t["code"] for i, t in enumerate(team_dicts)}
    probs = {}
    for i, code in inv.items():
        probs[code] = {
            "roundOf16": counts["round-of-16"][i] / n_sims,
            "quarter": counts["quarter-final"][i] / n_sims,
            "semi": counts["semi-final"][i] / n_sims,
            "final": counts["final"][i] / n_sims,
            "champion": counts["champion"][i] / n_sims,
        }
    return probs


# --------------------------------------------------------------------------- #
# Player tournament statistics (generated, minutes-aware)
# --------------------------------------------------------------------------- #
def allocate_player_stats(team_players, record, gen) -> None:
    played = max(1, record["played"])
    team_gf = record["gf"]
    team_ga = record["ga"]

    starters = sorted(team_players, key=lambda p: -p["rating"])[:11]
    starter_ids = {p["id"] for p in starters}

    # goal / assist distribution weights
    def goal_w(p):
        return {"FWD": 1.0, "MID": 0.5, "DEF": 0.12, "GK": 0.0}[p["position"]] * \
            (0.4 + (p["rating"] - 60) / 40)

    def assist_w(p):
        return {"FWD": 0.7, "MID": 1.0, "DEF": 0.35, "GK": 0.02}[p["position"]] * \
            (0.4 + (p["rating"] - 60) / 40)

    gw = np.array([max(0.0, goal_w(p)) for p in team_players])
    gw = gw / gw.sum() if gw.sum() > 0 else gw
    goals_alloc = gen.multinomial(team_gf, gw) if team_gf > 0 else np.zeros(len(team_players), int)

    n_assists = int(round(team_gf * 0.72))
    aw = np.array([max(0.0, assist_w(p)) for p in team_players])
    aw = aw / aw.sum() if aw.sum() > 0 else aw
    assists_alloc = gen.multinomial(n_assists, aw) if n_assists > 0 else np.zeros(len(team_players), int)

    clean_sheets = sum(1 for _ in range(played) if team_ga == 0)  # coarse
    for i, p in enumerate(team_players):
        is_starter = p["id"] in starter_ids
        if is_starter:
            apps = played
            minutes = int(clamp(gen.normal(0.92, 0.06) * played * 90, played * 55, played * 92))
        else:
            apps = int(gen.integers(0, played + 1))
            minutes = int(apps * gen.integers(8, 42)) if apps else 0

        goals = int(goals_alloc[i])
        assists = int(assists_alloc[i])
        pos = p["position"]
        rating = p["rating"]
        m90 = max(0.3, minutes / 90)

        xg = round(max(0.0, goals * 0.85 + gen.normal(0.08, 0.05) * m90), 2)
        xa = round(max(0.0, assists * 0.8 + gen.normal(0.06, 0.04) * m90), 2)
        shots = int(max(goals, gen.poisson({"FWD": 2.2, "MID": 1.1, "DEF": 0.4, "GK": 0.0}[pos] * m90)))
        sot = int(clamp(round(shots * gen.uniform(0.34, 0.5)), goals, max(goals, shots)))
        pass_rate = {"FWD": 22, "MID": 42, "DEF": 46, "GK": 24}[pos]
        passes = int(max(0, gen.normal(pass_rate, 6) * m90))
        pass_acc = round(clamp(gen.normal(78 + (rating - 70) * 0.4, 4), 55, 95), 1)
        key_passes = int(max(0, gen.poisson((assist_w(p) + 0.2) * m90)))
        tackles = int(max(0, gen.poisson({"FWD": 0.6, "MID": 1.6, "DEF": 2.2, "GK": 0.1}[pos] * m90)))
        interceptions = int(max(0, gen.poisson({"FWD": 0.3, "MID": 1.1, "DEF": 1.8, "GK": 0.2}[pos] * m90)))
        duels = int(max(0, gen.poisson(2.4 * m90)))
        yellows = int(gen.poisson(0.25 * apps))
        reds = 1 if gen.random() < 0.02 * apps else 0

        stats = {
            "appearances": apps, "minutes": minutes, "goals": goals, "assists": assists,
            "xg": xg, "xa": xa, "shots": shots, "shotsOnTarget": sot,
            "passes": passes, "passAccuracy": pass_acc, "keyPasses": key_passes,
            "tackles": tackles, "interceptions": interceptions, "duelsWon": duels,
            "yellowCards": min(yellows, apps if apps else 0), "redCards": reds,
            "saves": None, "cleanSheets": None, "goalsConceded": None,
        }
        if pos == "GK":
            gk_apps = apps
            stats["saves"] = int(max(0, gen.poisson(3.0 * gk_apps)))
            stats["goalsConceded"] = team_ga if is_starter else int(gen.integers(0, 3))
            stats["cleanSheets"] = clean_sheets if is_starter else 0
            stats["goals"] = 0
            stats["assists"] = min(stats["assists"], 0)

        contribution = clamp(
            (rating - 55) / 39 * 55 + goals * 6 + assists * 4 +
            (minutes / (played * 90)) * 14 + (5 if is_starter else 0),
            8, 99)
        p["stats"] = stats
        p["contribution"] = round(float(contribution), 1)
        p["isKeyPlayer"] = False  # set later (top per team)
        # short form trend around rating
        p["form"] = [
            {"label": f"M{k+1}", "rating": round(float(clamp(gen.normal(rating / 10, 0.6), 4.5, 9.9)), 1)}
            for k in range(min(apps, 5) or 1)
        ]
        p["bio"] = _player_bio(p)


def _player_bio(p: dict) -> str:
    pos_word = {"GK": "goalkeeper", "DEF": "defender", "MID": "midfielder",
                "FWD": "forward"}[p["position"]]
    cap = " and captains the side" if p.get("isCaptain") else ""
    return (f"{p['name']} is a {p['age']}-year-old {p['detailedPosition'].lower()} "
            f"({pos_word}) for {p['country']}, playing club football at "
            f"{p['club']}{cap}. Ratings and statistics are model-generated demo data.")


# --------------------------------------------------------------------------- #
# Team narrative
# --------------------------------------------------------------------------- #
def team_narrative(strength: dict, status: str, host: bool) -> tuple[list[str], list[str]]:
    strengths, weaknesses = [], []
    if strength["attack"] >= 72:
        strengths.append("Potent, high-scoring attack")
    if strength["defense"] >= 72:
        strengths.append("Miserly, well-drilled defense")
    if strength["squad"] >= 78:
        strengths.append("Elite squad depth")
    if strength["form"] >= 68:
        strengths.append("Strong recent form")
    if strength["momentum"] >= 70:
        strengths.append("Riding positive momentum")
    if host:
        strengths.append("Home-tournament advantage")
    if strength["experience"] >= 70:
        strengths.append("Tournament-tested, experienced core")

    if strength["attack"] < 45:
        weaknesses.append("Struggles to create clear chances")
    if strength["defense"] < 45:
        weaknesses.append("Defensively vulnerable")
    if strength["form"] < 40:
        weaknesses.append("Patchy recent results")
    if strength["experience"] < 40:
        weaknesses.append("Relatively inexperienced squad")
    if strength["squad"] < 45:
        weaknesses.append("Limited strength in depth")
    if status == "eliminated":
        weaknesses.append("Eliminated in the group stage")

    if not strengths:
        strengths.append("Balanced, hard-to-break-down side")
    if not weaknesses:
        weaknesses.append("Few obvious weaknesses")
    return strengths[:4], weaknesses[:4]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    teams_raw = read_json(os.path.join(PROCESSED_DIR, "teams.json"))
    squads = read_json(os.path.join(PROCESSED_DIR, "squads.json"))
    wc_feat = read_json(os.path.join(PROCESSED_DIR, "wc_features.json"))
    ts = read_json(os.path.join(PROCESSED_DIR, "team_strength.json"))
    qual = read_json(os.path.join(PROCESSED_DIR, "qualification.json"))
    meta = read_json(os.path.join(MODELS_DIR, "meta.json"))

    models = load_models()
    feat_matches = wc_feat["matches"]
    X = np.array([m["X"] for m in feat_matches], dtype=float)
    probs = per_model_probs(models, X)

    # average importance across models -> a representative "why" signal
    avg_importance = {f: 0.0 for f in FEATURE_ORDER}
    for mdl in ("elo", "logreg", "rf", "xgb"):
        for item in meta["importances"][mdl]:
            avg_importance[item["feature"]] += item["importance"] / 4.0
    stats = meta["feature_stats"]

    name_by_code = {t["code"]: t["name"] for t in teams_raw}

    # ---- raw predictions (per match, per model) + factors ----------------
    pred_rows = []
    for i, m in enumerate(feat_matches):
        home, away = m["home"], m["away"]
        pred_rows.append({
            "id": m["id"], "home": home, "away": away,
            "stage": m["stage"], "status": m["status"], "y": m["y"],
            "probs": {k: [round(float(x), 5) for x in probs[k][i]] for k in probs},
            "factors": build_factors(m["feats"], avg_importance, stats,
                                     name_by_code[home], name_by_code[away]),
        })
    write_json_pretty(os.path.join(OUTPUTS_DIR, "predictions.json"),
                      {"feature_order": FEATURE_ORDER, "matches": pred_rows})

    # ---- Championship Monte-Carlo ----------------------------------------
    ranked32 = set(qual["ranked32"])
    bracket_codes = qual["bracketPositions"]
    squad_score = {c: ts["strength"][c]["squad"] for c in ts["strength"]}
    gen = rng("mc")
    champ_now = run_championship(teams_raw, bracket_codes, ts["elo_current"],
                                 squad_score, N_SIMS, gen)

    # champion-odds history across Elo snapshots (active teams only)
    snap_labels = [("pre", "Pre-tournament"), ("md1", "Matchday 1"),
                   ("md2", "Matchday 2"), ("md3", "Group stage")]
    snapshots = dict(wc_feat["elo_snapshots"])
    snapshots["md3"] = wc_feat["elo_current"]
    history_probs = {}
    for key, _label in snap_labels:
        elo_snap = snapshots.get(key, ts["elo_current"])
        gh = rng(f"mc-{key}")
        history_probs[key] = run_championship(teams_raw, bracket_codes, elo_snap,
                                              squad_score, N_SIMS_HISTORY, gh)

    # ---- Player stats -----------------------------------------------------
    by_team_players: dict[str, list] = {}
    for p in squads:
        by_team_players.setdefault(p["countryCode"], []).append(p)
    records = qual["records"]
    for code, plist in by_team_players.items():
        allocate_player_stats(plist, records[code], rng(f"players-{code}"))
        top = sorted(plist, key=lambda x: -x["contribution"])[:4]
        for p in top:
            p["isKeyPlayer"] = True

    players_out = []
    for code, plist in by_team_players.items():
        for p in plist:
            players_out.append({
                "id": p["id"], "name": p["name"], "countryCode": code,
                "country": p["country"], "iso2": p["iso2"], "position": p["position"],
                "detailedPosition": p["detailedPosition"], "shirtNumber": p["shirtNumber"],
                "age": p["age"], "club": p["club"], "clubCountry": p["clubCountry"],
                "rating": p["rating"], "contribution": p["contribution"],
                "isCaptain": p["isCaptain"], "isKeyPlayer": p["isKeyPlayer"],
                "stats": p["stats"], "form": p["form"], "bio": p["bio"],
            })
    players_out.sort(key=lambda x: (-x["rating"], x["name"]))
    publish("players.json", players_out)

    # ---- Teams ------------------------------------------------------------
    elos = [t["elo0"] for t in teams_raw]
    elo_cur_vals = list(ts["elo_current"].values())
    lo_e, hi_e = min(elo_cur_vals), max(elo_cur_vals)

    teams_out = []
    for t in teams_raw:
        code = t["code"]
        st = ts["strength"][code]
        fm = ts["form"][code]
        elo_cur = ts["elo_current"][code]
        active = code in ranked32
        form_100 = round(clamp(fm["form_ppg"] / 3.0 * 100, 3, 99), 1)
        momentum_100 = round(clamp(fm["momentum"] / 9.0 * 100, 3, 99), 1)
        elo_100 = scale_0_100(elo_cur, lo_e, hi_e)
        overall = round(0.55 * elo_100 + 0.30 * st["squad"] + 0.15 * form_100, 1)
        strength = {
            "overall": overall, "attack": st["attack"], "defense": st["defense"],
            "form": form_100, "squad": st["squad"], "momentum": momentum_100,
            "experience": st["experience"],
        }
        cp = champ_now[code]
        rec = records[code]
        record = {
            "played": rec["played"], "won": rec["won"], "drawn": rec["drawn"],
            "lost": rec["lost"], "gf": rec["gf"], "ga": rec["ga"], "gd": rec["gd"],
            "points": rec["points"], "groupRank": rec.get("groupRank"),
        }
        champ_hist = []
        if active:
            for key, label in snap_labels:
                champ_hist.append({"label": label,
                                   "prob": round(history_probs[key][code]["champion"], 5)})
        key_ids = [p["id"] for p in sorted(by_team_players[code],
                                           key=lambda x: -x["contribution"])[:4]]
        strengths, weaknesses = team_narrative(strength, "active" if active else "eliminated", t["host"])
        teams_out.append({
            "code": code, "iso2": t["iso2"], "name": t["name"],
            "confederation": t["confederation"], "group": t["group"],
            "colors": t["colors"], "elo": round(elo_cur, 1), "eloInitial": t["elo0"],
            "fifaRank": t["fifaRank"],
            "status": "active" if active else "eliminated",
            "eliminatedRound": None if active else "group",
            "strength": strength, "record": record,
            "championProb": round(cp["champion"], 5),
            "advance": {
                "roundOf32": 1.0 if active else 0.0,
                "roundOf16": round(cp["roundOf16"], 5),
                "quarter": round(cp["quarter"], 5),
                "semi": round(cp["semi"], 5),
                "final": round(cp["final"], 5),
                "champion": round(cp["champion"], 5),
            },
            "strengths": strengths, "weaknesses": weaknesses,
            "keyPlayerIds": key_ids, "championProbHistory": champ_hist,
        })
    teams_out.sort(key=lambda x: -x["championProb"])
    publish("teams.json", teams_out)

    # ---- Rankings ---------------------------------------------------------
    build_rankings(teams_out, pred_rows, feat_matches)

    # ---- Methodology ------------------------------------------------------
    build_methodology(meta, len(pred_rows))

    print(f"[predict] matches={len(pred_rows)} players={len(players_out)} "
          f"top_champion={teams_out[0]['name']} ({teams_out[0]['championProb']*100:.1f}%)")


def build_rankings(teams_out, pred_rows, feat_matches) -> None:
    # per-team average ensemble (equal weight) confidence in their own matches
    eq = np.array([0.25, 0.25, 0.25, 0.25])
    conf_sum: dict[str, list] = {}
    for row, fm in zip(pred_rows, feat_matches):
        mats = np.array([row["probs"][k] for k in ("elo", "logreg", "rf", "xgb")])
        P = (eq[:, None] * mats).sum(axis=0)
        P = P / P.sum()
        for side, code in (("home", fm["home"]), ("away", fm["away"])):
            win_p = P[0] if side == "home" else P[2]
            conf_sum.setdefault(code, []).append(win_p)
    model_conf = {c: float(np.mean(v)) * 100 for c, v in conf_sum.items()}

    meta_by_code = {t["code"]: t for t in teams_out}

    def view(vid, name, desc, unit, fmt, valuefn):
        entries = []
        for t in teams_out:
            entries.append({
                "code": t["code"], "name": t["name"], "iso2": t["iso2"],
                "confederation": t["confederation"], "group": t["group"],
                "value": round(float(valuefn(t)), 4),
            })
        entries.sort(key=lambda e: -e["value"])
        for i, e in enumerate(entries, 1):
            e["rank"] = i
        return {"id": vid, "name": name, "description": desc, "unit": unit,
                "format": fmt, "entries": entries}

    views = [
        view("champion", "Championship Odds", "Monte-Carlo probability of winning the World Cup",
             "%", "percent", lambda t: t["championProb"] * 100),
        view("overall", "Team Strength", "Blended Elo + squad + form rating",
             "", "rating", lambda t: t["strength"]["overall"]),
        view("elo", "Elo Rating", "Current Elo rating after the group stage",
             "", "number", lambda t: t["elo"]),
        view("form", "Recent Form", "Points-per-game form over the last five matches",
             "", "rating", lambda t: t["strength"]["form"]),
        view("attack", "Attack Strength", "Attacking quality from squad ratings",
             "", "rating", lambda t: t["strength"]["attack"]),
        view("defense", "Defense Strength", "Defensive quality from squad ratings",
             "", "rating", lambda t: t["strength"]["defense"]),
        view("squad", "Squad Strength", "Overall squad quality & depth",
             "", "rating", lambda t: t["strength"]["squad"]),
        view("momentum", "Momentum", "Points won across the most recent matches",
             "", "rating", lambda t: t["strength"]["momentum"]),
        view("confidence", "Model Confidence", "Average model win-probability across the team's fixtures",
             "%", "percent", lambda t: model_conf.get(t["code"], 0.0)),
    ]
    publish("rankings.json", {"views": views})


def build_methodology(meta, n_matches) -> None:
    methodology = {
        "pipeline": [
            {"id": "ingest", "title": "Raw ingestion",
             "description": "Builds the 48-team field, a pot-based group draw, latent 'true' strengths, a synthetic 2019-2025 international match history (training data) and the canonical 2026 bracket.",
             "outputs": ["data/raw/teams.json", "data/raw/history.json", "data/raw/wc_matches.json", "data/raw/squads.json"]},
            {"id": "transform", "title": "Validation & cleaning",
             "description": "Schema, range and referential-integrity checks; chronological ordering; outcome labelling. Fails loudly on malformed data.",
             "outputs": ["data/processed/*.json"]},
            {"id": "features", "title": "Feature engineering",
             "description": "Leakage-free rolling features: Elo, recent form, goals for/against, xG trend, rest days, head-to-head, squad strength, host & stage flags.",
             "outputs": ["data/processed/train.json", "data/processed/wc_features.json"]},
            {"id": "train", "title": "Model training",
             "description": "Trains Elo baseline, Logistic Regression, Random Forest and XGBoost on the synthetic history ONLY (no World Cup match is ever seen in training).",
             "outputs": ["ml/models/*.joblib", "ml/models/meta.json"]},
            {"id": "predict", "title": "Prediction & simulation",
             "description": "Per-match probabilities + explanation factors, a 20k-tournament Monte-Carlo for title odds, team metrics and player statistics.",
             "outputs": ["public/data/teams.json", "public/data/players.json", "public/data/rankings.json"]},
            {"id": "evaluate", "title": "Backtest & self-improvement",
             "description": "Scores every model against completed matches (accuracy, log-loss, Brier, calibration), re-ranks them and updates the ensemble weights (∝ 1/log-loss).",
             "outputs": ["public/data/models.json", "public/data/matches.json", "public/data/summary.json"]},
        ],
        "dataSources": [
            {"name": "48-team field, Elo ratings & colours", "kind": "static",
             "description": "Curated from publicly known FIFA/Elo values and national colours. The exact qualified field is a projection.",
             "license": "Public facts / CC0-style reference data"},
            {"name": "International match history 2019-2025", "kind": "generated",
             "description": "Synthetic matches simulated from latent team strengths — used only for model training.",
             "license": "Generated (this project)"},
            {"name": "Squads & player statistics", "kind": "generated",
             "description": "26 generated players per nation with culturally-plausible names, plus minutes-aware tournament stats. No real player data or headshots are used.",
             "license": "Generated (this project)"},
            {"name": "Country flags", "kind": "static",
             "description": "SVG flags rendered via the open-source flag-icons library.",
             "license": "flag-icons — MIT (code) / public-domain (flags)"},
        ],
        "features": [{"feature": f, "label": FEATURE_LABELS[f]} for f in FEATURE_ORDER],
        "models": [
            {"id": "elo", "name": "Elo Baseline", "summary": "Analytic two-stage Elo with a fitted draw model. A strong, transparent benchmark."},
            {"id": "logreg", "name": "Logistic Regression", "summary": "Multinomial regression on standardised features — interpretable coefficients."},
            {"id": "rf", "name": "Random Forest", "summary": "Bagged decision trees capturing non-linear feature interactions."},
            {"id": "xgb", "name": "XGBoost", "summary": "Gradient-boosted trees — typically the strongest single learner."},
            {"id": "ensemble", "name": "Weighted Ensemble", "summary": "Performance-weighted blend of all models (weights ∝ 1/log-loss)."},
        ],
        "notes": [
            "Predictions are probabilistic estimates, not guarantees.",
            "Models are trained only on historical (pre-tournament) data; completed matches are used exclusively for backtesting — preventing data leakage.",
            "The Round-of-32 seeding uses a simplified strength seeding rather than FIFA's official pairing table.",
            "Title odds come from a Monte-Carlo simulation using a calibrated Elo+squad model; per-match modal probabilities come from the full ML ensemble.",
            f"{n_matches} World Cup matches are covered end-to-end.",
        ],
        "generatedAt": now_iso(),
    }
    publish("methodology.json", methodology)


if __name__ == "__main__":
    main()
