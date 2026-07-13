"""
predict.py  —  Stage 5: prediction generation
==============================================
Loads the trained models and generates, for every 2026 World Cup match, the
per-model win/draw/loss probabilities plus transparent "top contributing
factors" for the explanation modal. It also:

  * runs a vectorised Monte-Carlo championship simulation (20k tournaments)
    that FIXES every completed knockout result and simulates only the matches
    still to be played — so title odds & advancement probabilities reflect the
    live tournament state,
  * projects the two not-yet-scheduled matches (third-place play-off & final)
    from their most-likely participants and predicts them with the full model
    stack,
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
    TOURNAMENT, HOST, HOME_ADV,
)
from modeling import elo_baseline_proba
from tournament import simulate_bracket

N_SIMS = 20000
N_SIMS_HISTORY = 8000
CLASS_NAMES = ["home", "draw", "away"]
HOSTS = {"USA", "CAN", "MEX"}


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
# Championship Monte-Carlo (respects completed knockout results)
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


def _advance_from_reach(reach: dict, champion: np.ndarray, i: int, n: int) -> dict:
    return {
        "roundOf32": round(reach["round-of-32"][i] / n, 5),
        "roundOf16": round(reach["round-of-16"][i] / n, 5),
        "quarter": round(reach["quarter-final"][i] / n, 5),
        "semi": round(reach["semi-final"][i] / n, 5),
        "final": round(reach["final"][i] / n, 5),
        "champion": round(champion[i] / n, 5),
    }


# --------------------------------------------------------------------------- #
# Feature vector for a PROJECTED matchup (final / third place, teams unknown
# until the semis are played). Built from the same current team-state metrics
# used everywhere else; head-to-head & rest are neutral approximations, which is
# transparent and only affects these two look-ahead fixtures.
# --------------------------------------------------------------------------- #
def projected_features(h: str, a: str, ts: dict, squad_score: dict) -> tuple[list, dict]:
    fm = ts["form"]
    elo = ts["elo_current"]
    host_adv = 1.0 if (h in HOSTS and a not in HOSTS) else (
        -1.0 if (a in HOSTS and h not in HOSTS) else 0.0)
    feats = {
        "elo_diff": elo[h] - elo[a],
        "form_diff": fm[h]["form_ppg"] - fm[a]["form_ppg"],
        "gf_diff": fm[h]["gf_recent"] - fm[a]["gf_recent"],
        "ga_diff": fm[a]["ga_recent"] - fm[h]["ga_recent"],
        "xg_diff": fm[h]["xg_recent"] - fm[a]["xg_recent"],
        "squad_diff": (squad_score[h] - squad_score[a]) / 10.0,
        "rest_diff": 0.0,
        "h2h_diff": 0.0,
        "host_adv": host_adv,
        "stage_knockout": 1.0,
    }
    vec = [round(float(feats[f]), 4) for f in FEATURE_ORDER]
    feats = {k: round(v, 4) for k, v in feats.items()}
    return vec, feats


# --------------------------------------------------------------------------- #
# Player tournament statistics (generated, minutes-aware)
# --------------------------------------------------------------------------- #
def allocate_player_stats(team_players, record, gen) -> None:
    played = max(1, record["played"])
    team_gf = record["gf"]
    team_ga = record["ga"]

    starters = sorted(team_players, key=lambda p: -p["rating"])[:11]
    starter_ids = {p["id"] for p in starters}

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
_ELIM_TEXT = {
    "group": "Eliminated in the group stage",
    "round-of-32": "Knocked out in the round of 32",
    "round-of-16": "Knocked out in the round of 16",
    "quarter-final": "Knocked out in the quarter-finals",
    "semi-final": "Beaten in the semi-finals",
    "third-place": "Finished fourth",
    "final": "Runners-up",
}


def team_narrative(strength: dict, active: bool, host: bool,
                   elim_round: str | None) -> tuple[list[str], list[str]]:
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
    if not active and elim_round:
        weaknesses.insert(0, _ELIM_TEXT.get(elim_round, "Eliminated"))

    if not strengths:
        strengths.append("Balanced, hard-to-break-down side")
    if not weaknesses:
        weaknesses.append("Few obvious weaknesses")
    return strengths[:4], weaknesses[:4]


# --------------------------------------------------------------------------- #
# Elimination / advancement from the REAL knockout results
# --------------------------------------------------------------------------- #
def compute_status(wc_matches, ranked32):
    """Return (active:set, eliminated_round:dict[code -> stage])."""
    active: set[str] = set()
    elim: dict[str, str] = {}
    ranked = set(ranked32)
    # All 48 start active; the 16 who didn't reach the round of 32 go out in the
    # group stage, then every completed knockout eliminates its loser.
    for m in wc_matches:
        for side in ("home", "away"):
            if m[side]:
                active.add(m[side])
    for code in list(active):
        if code not in ranked:
            elim[code] = "group"
    for m in wc_matches:
        if m["knockout"] and m["status"] == "completed" and m["winner"]:
            loser = m["away"] if m["winner"] == "home" else m["home"]
            if loser:
                elim[loser] = m["stage"]
    active = {c for c in active if c not in elim}
    return active, elim


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    teams_raw = read_json(os.path.join(PROCESSED_DIR, "teams.json"))
    squads = read_json(os.path.join(PROCESSED_DIR, "squads.json"))
    wc_feat = read_json(os.path.join(PROCESSED_DIR, "wc_features.json"))
    wc_matches = read_json(os.path.join(PROCESSED_DIR, "wc_matches.json"))
    ts = read_json(os.path.join(PROCESSED_DIR, "team_strength.json"))
    qual = read_json(os.path.join(PROCESSED_DIR, "qualification.json"))
    meta = read_json(os.path.join(MODELS_DIR, "meta.json"))

    models = load_models()
    feat_matches = wc_feat["matches"]
    X = np.array([m["X"] for m in feat_matches], dtype=float)
    probs = per_model_probs(models, X)

    avg_importance = {f: 0.0 for f in FEATURE_ORDER}
    for mdl in ("elo", "logreg", "rf", "xgb"):
        for item in meta["importances"][mdl]:
            avg_importance[item["feature"]] += item["importance"] / 4.0
    stats = meta["feature_stats"]

    name_by_code = {t["code"]: t["name"] for t in teams_raw}
    squad_score = {c: ts["strength"][c]["squad"] for c in ts["strength"]}

    # ---- Championship Monte-Carlo (fixes completed knockout results) ------
    knockout = qual["knockout"]
    eff_cur, idx = build_eff(teams_raw, ts["elo_current"], squad_score)
    inv = {i: t["code"] for i, t in enumerate(teams_raw)}
    champ = simulate_bracket(knockout, eff_cur, idx, N_SIMS, rng("mc"))
    reach, champion, proj = champ["reach"], champ["champion"], champ["proj"]

    # ---- raw predictions (per match, per model) + factors -----------------
    pred_rows = []
    for i, m in enumerate(feat_matches):
        home, away = m["home"], m["away"]
        pred_rows.append({
            "id": m["id"], "home": home, "away": away,
            "stage": m["stage"], "status": m["status"], "y": m["y"],
            "probs": {k: [round(float(x), 5) for x in probs[k][i]] for k in probs},
            "factors": build_factors(m["feats"], avg_importance, stats,
                                     name_by_code[home], name_by_code[away]),
            "projected": False,
        })

    # ---- Projected look-ahead fixtures (third-place & final) --------------
    # These have no confirmed teams yet, so we take the most-likely participants
    # from the simulation and predict them with the full model stack.
    wc_by_num = {m["num"]: m for m in wc_matches if m["num"] is not None}
    have_ids = {r["id"] for r in pred_rows}
    proj_rows = []
    for num in sorted(proj):
        wm = wc_by_num.get(num)
        if wm is None or wm["id"] in have_ids or wm["home"] or wm["away"]:
            continue  # only the genuinely TBD matches (final / third place)
        h, a = inv[proj[num]["homeIdx"]], inv[proj[num]["awayIdx"]]
        vec, feats = projected_features(h, a, ts, squad_score)
        proj_rows.append({"id": wm["id"], "home": h, "away": a,
                          "stage": wm["stage"], "feats": feats, "X": vec})
    if proj_rows:
        Xp = np.array([r["X"] for r in proj_rows], dtype=float)
        pprobs = per_model_probs(models, Xp)
        for j, r in enumerate(proj_rows):
            pred_rows.append({
                "id": r["id"], "home": r["home"], "away": r["away"],
                "stage": r["stage"], "status": "upcoming", "y": None,
                "probs": {k: [round(float(x), 5) for x in pprobs[k][j]] for k in pprobs},
                "factors": build_factors(r["feats"], avg_importance, stats,
                                         name_by_code[r["home"]], name_by_code[r["away"]]),
                "projected": True,
            })

    write_json_pretty(os.path.join(OUTPUTS_DIR, "predictions.json"),
                      {"feature_order": FEATURE_ORDER, "matches": pred_rows})

    # ---- Champion-odds history: rewind the sim to each completed round -----
    snapshots = wc_feat["elo_snapshots"]
    snap_specs = [("group", "Group stage", -1),
                  ("round-of-32", "Round of 32", 0),
                  ("round-of-16", "Round of 16", 1)]
    history_champ = {}
    for key, _label, rank in snap_specs:
        elo_snap = snapshots.get(key, ts["elo_current"])
        eff_s, _ = build_eff(teams_raw, elo_snap, squad_score)
        res = simulate_bracket(knockout, eff_s, idx, N_SIMS_HISTORY,
                               rng(f"mc-{key}"), as_of_rank=rank)
        history_champ[key] = res["champion"] / N_SIMS_HISTORY
    hist_labels = [(k, lbl) for k, lbl, _ in snap_specs] + [("now", "Quarter-finals")]

    # ---- Player stats -----------------------------------------------------
    by_team_players: dict[str, list] = {}
    for p in squads:
        by_team_players.setdefault(p["countryCode"], []).append(p)
    records = qual["records"]
    for code, plist in by_team_players.items():
        allocate_player_stats(plist, records[code], rng(f"players-{code}"))
        for p in sorted(plist, key=lambda x: -x["contribution"])[:4]:
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
    active, elim_round = compute_status(wc_matches, qual["ranked32"])
    elo_pre = ts["elo_pre"]
    pre_rank = {c: r for r, (c, _v) in enumerate(
        sorted(elo_pre.items(), key=lambda kv: -kv[1]), start=1)}

    elo_cur_vals = list(ts["elo_current"].values())
    lo_e, hi_e = min(elo_cur_vals), max(elo_cur_vals)

    teams_out = []
    for t in teams_raw:
        code = t["code"]
        st = ts["strength"][code]
        fm = ts["form"][code]
        elo_cur = ts["elo_current"][code]
        is_active = code in active
        i = idx[code]
        form_100 = round(clamp(fm["form_ppg"] / 3.0 * 100, 3, 99), 1)
        momentum_100 = round(clamp(fm["momentum"] / 9.0 * 100, 3, 99), 1)
        elo_100 = scale_0_100(elo_cur, lo_e, hi_e)
        overall = round(0.55 * elo_100 + 0.30 * st["squad"] + 0.15 * form_100, 1)
        strength = {
            "overall": overall, "attack": st["attack"], "defense": st["defense"],
            "form": form_100, "squad": st["squad"], "momentum": momentum_100,
            "experience": st["experience"],
        }
        rec = records[code]
        record = {
            "played": rec["played"], "won": rec["won"], "drawn": rec["drawn"],
            "lost": rec["lost"], "gf": rec["gf"], "ga": rec["ga"], "gd": rec["gd"],
            "points": rec["points"], "groupRank": rec.get("groupRank"),
        }
        champ_prob = round(champion[i] / N_SIMS, 5)
        champ_hist = []
        if code in set(qual["ranked32"]):
            for key, label in hist_labels:
                prob = (champ_prob if key == "now"
                        else round(float(history_champ[key][i]), 5))
                champ_hist.append({"label": label, "prob": prob})
        key_ids = [p["id"] for p in sorted(by_team_players[code],
                                           key=lambda x: -x["contribution"])[:4]]
        strengths, weaknesses = team_narrative(
            strength, is_active, t["host"], elim_round.get(code))
        teams_out.append({
            "code": code, "iso2": t["iso2"], "name": t["name"],
            "confederation": t["confederation"], "group": t["group"],
            "colors": t["colors"], "elo": round(elo_cur, 1),
            "eloInitial": round(elo_pre[code], 1), "fifaRank": pre_rank[code],
            "status": "active" if is_active else "eliminated",
            "eliminatedRound": None if is_active else elim_round.get(code, "group"),
            "strength": strength, "record": record,
            "championProb": champ_prob,
            "advance": _advance_from_reach(reach, champion, i, N_SIMS),
            "strengths": strengths, "weaknesses": weaknesses,
            "keyPlayerIds": key_ids, "championProbHistory": champ_hist,
        })
    teams_out.sort(key=lambda x: -x["championProb"])
    publish("teams.json", teams_out)

    # ---- Rankings ---------------------------------------------------------
    build_rankings(teams_out, pred_rows)

    # ---- Methodology ------------------------------------------------------
    build_methodology(meta, len(pred_rows))

    top = teams_out[0]
    print(f"[predict] matches={len(pred_rows)} players={len(players_out)} "
          f"active={len(active)} top_champion={top['name']} "
          f"({top['championProb']*100:.1f}%)")


def build_rankings(teams_out, pred_rows) -> None:
    eq = np.array([0.25, 0.25, 0.25, 0.25])
    conf_sum: dict[str, list] = {}
    for row in pred_rows:
        mats = np.array([row["probs"][k] for k in ("elo", "logreg", "rf", "xgb")])
        P = (eq[:, None] * mats).sum(axis=0)
        P = P / P.sum()
        for side, code in (("home", row["home"]), ("away", row["away"])):
            win_p = P[0] if side == "home" else P[2]
            conf_sum.setdefault(code, []).append(win_p)
    model_conf = {c: float(np.mean(v)) * 100 for c, v in conf_sum.items()}

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
        view("elo", "Elo Rating", "Live Elo rating at the current tournament state",
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
             "description": "Parses the cached CC0 sources: every men's international 1872→2026 (martj42) and the real 2026 group draw, fixtures, results & knockout bracket (openfootball). Emits the 48-team field, training history and the World Cup schedule.",
             "outputs": ["data/raw/teams.json", "data/raw/history.json", "data/raw/wc_matches.json", "data/raw/qualification.json"]},
            {"id": "transform", "title": "Validation & cleaning",
             "description": "Schema, range and referential-integrity checks; chronological ordering; outcome labelling. Match status is derived from whether a real result exists, so the app tracks the live tournament. Fails loudly on malformed data.",
             "outputs": ["data/processed/*.json"]},
            {"id": "features", "title": "Feature engineering",
             "description": "Leakage-free rolling features: real Elo (grown over the full match history), recent form, goals for/against, xG trend, rest days, head-to-head, squad strength, host & stage flags. Team Elo is snapshotted after each completed round.",
             "outputs": ["data/processed/train.json", "data/processed/wc_features.json"]},
            {"id": "train", "title": "Model training",
             "description": "Trains Elo baseline, Logistic Regression, Random Forest and XGBoost on real international matches from 2002 up to the opener ONLY (no World Cup match is ever seen in training).",
             "outputs": ["ml/models/*.joblib", "ml/models/meta.json"]},
            {"id": "predict", "title": "Prediction & simulation",
             "description": "Per-match probabilities + explanation factors and a 20k-tournament Monte-Carlo that fixes completed knockout results and simulates only the matches still to play — producing live title odds, advancement probabilities, team metrics and player statistics.",
             "outputs": ["public/data/teams.json", "public/data/players.json", "public/data/rankings.json"]},
            {"id": "evaluate", "title": "Backtest & self-improvement",
             "description": "Scores every model against completed matches (accuracy, log-loss, Brier, calibration), re-ranks them and updates the ensemble weights (∝ 1/log-loss).",
             "outputs": ["public/data/models.json", "public/data/matches.json", "public/data/summary.json"]},
        ],
        "dataSources": [
            {"name": "International match results (1872→2026)", "kind": "cached",
             "description": "martj42/international_results — every men's full international. Used for model training and to compute each nation's real Elo. Cached locally as data/source/martj42_results.csv.",
             "license": "CC0 1.0 (public domain)"},
            {"name": "2026 World Cup fixtures, results & bracket", "kind": "cached",
             "description": "openfootball/worldcup (2026--usa) — the real group draw, kickoff times, scores and knockout bracket in the Football.TXT format. Cached locally as data/source/openfootball_cup*.txt.",
             "license": "CC0 1.0 (public domain)"},
            {"name": "Squads & player statistics", "kind": "generated",
             "description": "26 deterministically-generated players per nation with culturally-plausible names, plus minutes-aware tournament stats keyed to the real group results. No clean CC0 squad/headshot source exists, so no real player data or photos are used.",
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
            "Models are trained only on real internationals played before the World Cup; completed tournament matches are used exclusively for backtesting — preventing data leakage.",
            "Elo ratings are grown from a common 1500 baseline over the entire 1872→2026 match history, so each nation's pre-tournament strength is earned from real results.",
            "Title odds come from a Monte-Carlo simulation that fixes every completed knockout result and simulates only the remaining matches; per-match modal probabilities come from the full ML ensemble.",
            "The final and third-place play-off are shown as projected matchups (most-likely participants) until the semi-finals are played.",
            f"{n_matches} World Cup matches are covered end-to-end.",
        ],
        "generatedAt": now_iso(),
    }
    publish("methodology.json", methodology)


if __name__ == "__main__":
    main()
