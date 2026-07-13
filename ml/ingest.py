"""
ingest.py  —  Stage 1: raw data ingestion (REAL data)
=====================================================
Builds the raw, reproducible inputs for the pipeline from the cached CC0 source
files (see ml/sources.py). Everything is offline & deterministic — re-running
reproduces identical output.

  * teams (48)      — the real 2026 field + official group draw (common.py)
  * history         — every played men's international 1872→2026-06-10
                      (martj42, CC0) → training data + real Elo
  * wc_matches      — the real 2026 group draw, fixtures, results & knockout
                      bracket (openfootball, CC0); status is derived from whether
                      a real result exists, so the app tracks the live tournament
  * qualification   — real group tables + the real Round-of-32 bracket + a
                      knockout tree (with W##/L## feeders) for the simulator
  * squads          — 26 deterministically *generated* players per nation
                      (no clean CC0 squad source exists — documented in README),
                      keyed to the real teams

No World Cup match is ever used for training (leakage-free): history stops the
day before the opener.
"""
from __future__ import annotations

import os

import numpy as np

from common import (
    load_teams, rng,
    NAME_CULTURE, FIRST_NAMES, LAST_NAMES, BIG_CLUBS, MID_CLUBS, SMALL_CLUBS,
    POSITION_DETAIL, RAW_DIR, write_json, write_json_pretty,
)
from tournament import blank_record, apply_result, group_tables
import sources as S


# --------------------------------------------------------------------------- #
# Historical international matches (real, martj42 — training + Elo)
# --------------------------------------------------------------------------- #
def build_history() -> list[dict]:
    rows = S.parse_martj42()
    history: list[dict] = []
    for r in rows:
        # Elo key: FIFA code for the 48 WC teams, raw name for everyone else.
        hkey = r["home_code"] or f"~{r['home_name']}"
        akey = r["away_code"] or f"~{r['away_name']}"
        home_adv = 0 if r["neutral"] else 1     # neutral venue → no home edge
        history.append({
            "id": r["id"], "date": r["date"],
            "home": hkey, "away": akey,
            "home_code": r["home_code"], "away_code": r["away_code"],
            "home_name": r["home_name"], "away_name": r["away_name"],
            "home_adv": home_adv,
            "gh": r["gh"], "ga": r["ga"], "fh": r["gh"], "fa": r["ga"],
            "tournament": r["tournament"],
        })
    return history


# --------------------------------------------------------------------------- #
# Real 2026 World Cup fixtures, results & bracket (openfootball)
# --------------------------------------------------------------------------- #
def build_world_cup(teams):
    by_code = {t.code: t for t in teams}
    group_matches = S.parse_group_stage()
    knockout_matches = S.parse_knockouts()
    wc_matches = group_matches + knockout_matches

    # ---- Real group tables from real group results -----------------------
    records = {t.code: blank_record() for t in teams}
    for m in group_matches:
        apply_result(records[m["home"]], m["gh"], m["ga"])
        apply_result(records[m["away"]], m["ga"], m["gh"])
    tables = group_tables(records, by_code)

    # ---- Real Round-of-32 bracket straight from the source matchups ------
    r32 = sorted([m for m in knockout_matches if m["stage"] == "round-of-32"],
                 key=lambda m: m["num"])
    bracket_positions: list[str] = []
    for m in r32:
        bracket_positions += [m["home"], m["away"]]     # 32 codes, bracket order
    ranked32 = list(dict.fromkeys(bracket_positions))   # de-duped, order-preserving

    # ---- Knockout tree for the Monte-Carlo simulator ---------------------
    knockout_tree = []
    for m in sorted(knockout_matches, key=lambda m: m["num"]):
        winner_side = 0 if m["winner"] == "home" else (2 if m["winner"] == "away" else None)
        knockout_tree.append({
            "num": m["num"], "stage": m["stage"], "slot": m["slot"],
            "homeCode": m["home"], "awayCode": m["away"],
            "feedHome": m["feedHome"], "feedAway": m["feedAway"],
            "played": m["played"], "winnerSide": winner_side,
        })

    return wc_matches, records, tables, ranked32, bracket_positions, knockout_tree


# --------------------------------------------------------------------------- #
# Squad generation (deterministic demo players — no clean CC0 source exists)
# --------------------------------------------------------------------------- #
SQUAD_TEMPLATE = (
    ["GK"] * 3 + ["DEF"] * 8 + ["MID"] * 8 + ["FWD"] * 7
)  # 26 players


def team_base_rating(teams) -> dict[str, float]:
    elos = [t.elo0 for t in teams]
    lo, hi = min(elos), max(elos)
    base = {}
    for t in teams:
        base[t.code] = 62 + (t.elo0 - lo) / (hi - lo) * 27  # 62..89
    return base


def unique_name(culture: str, used: set, generator) -> str:
    firsts = FIRST_NAMES[culture]
    lasts = LAST_NAMES[culture]
    for _ in range(200):
        name = f"{generator.choice(firsts)} {generator.choice(lasts)}"
        if name not in used:
            used.add(name)
            return name
    name = f"{generator.choice(firsts)} {generator.choice(lasts)} {len(used)}"
    used.add(name)
    return name


def pick_club(rating: float, generator):
    if rating >= 82:
        pool = BIG_CLUBS if generator.random() < 0.8 else MID_CLUBS
    elif rating >= 74:
        pool = MID_CLUBS if generator.random() < 0.7 else BIG_CLUBS
    else:
        pool = SMALL_CLUBS if generator.random() < 0.65 else MID_CLUBS
    return tuple(pool[int(generator.integers(0, len(pool)))])


def generate_squads(teams) -> list[dict]:
    r = rng("squads")
    base = team_base_rating(teams)
    players: list[dict] = []
    for t in teams:
        culture = NAME_CULTURE.get(t.code, "english")
        used_names: set = set()
        team_base = base[t.code]
        shirts = list(range(1, 27))
        ratings = np.sort(r.normal(team_base, 4.2, size=26))[::-1]
        ratings[0] += 3.5  # star
        ratings[1] += 2.0
        squad_rows = []
        for i, pos in enumerate(SQUAD_TEMPLATE):
            rating = float(np.clip(ratings[i] + _pos_bias(pos, r), 55, 94))
            name = unique_name(culture, used_names, r)
            club, club_country = pick_club(rating, r)
            detail = POSITION_DETAIL[pos][int(r.integers(0, len(POSITION_DETAIL[pos])))]
            age = int(np.clip(r.normal(26.5, 3.6), 18, 39))
            squad_rows.append({
                "id": f"{t.code}-{i+1:02d}",
                "name": name, "countryCode": t.code, "country": t.name,
                "iso2": t.iso2, "position": pos, "detailedPosition": detail,
                "age": age, "club": club, "clubCountry": club_country,
                "rating": round(rating, 1),
            })
        squad_rows.sort(key=lambda x: (["GK", "DEF", "MID", "FWD"].index(x["position"]),
                                       -x["rating"]))
        gk_numbers = [1, 12, 23]
        gk_i = 0
        outfield = [n for n in shirts if n not in gk_numbers]
        r.shuffle(outfield)
        of_i = 0
        for row in squad_rows:
            if row["position"] == "GK":
                row["shirtNumber"] = gk_numbers[gk_i]
                gk_i += 1
            else:
                row["shirtNumber"] = outfield[of_i]
                of_i += 1
        cap = max(squad_rows, key=lambda x: x["rating"])
        for row in squad_rows:
            row["isCaptain"] = row["id"] == cap["id"]
        players.extend(squad_rows)
    return players


def _pos_bias(pos: str, generator) -> float:
    return {"GK": -1.0, "DEF": -0.5, "MID": 0.4, "FWD": 0.6}[pos] + generator.normal(0, 0.6)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    teams = load_teams()

    history = build_history()
    (wc_matches, records, tables, ranked32,
     bracket_positions, knockout_tree) = build_world_cup(teams)
    squads = generate_squads(teams)

    teams_raw = []
    for t in teams:
        teams_raw.append({
            "code": t.code, "iso2": t.iso2, "name": t.name,
            "confederation": t.confederation, "group": t.group, "pot": t.pot,
            "elo0": t.elo0, "fifaRank": t.fifa_rank, "host": t.host,
            "colors": {"primary": t.primary, "secondary": t.secondary},
        })

    write_json_pretty(os.path.join(RAW_DIR, "teams.json"), teams_raw)
    write_json(os.path.join(RAW_DIR, "history.json"), history)  # large — keep compact
    write_json_pretty(os.path.join(RAW_DIR, "wc_matches.json"), wc_matches)
    write_json_pretty(os.path.join(RAW_DIR, "squads.json"), squads)
    write_json_pretty(os.path.join(RAW_DIR, "qualification.json"), {
        "tables": tables,
        "ranked32": ranked32,
        "bracketPositions": bracket_positions,
        "records": records,
        "knockout": knockout_tree,
    })

    completed = sum(1 for m in wc_matches if m["played"])
    print(f"[ingest] teams={len(teams_raw)} history={len(history)} "
          f"wc_matches={len(wc_matches)} (completed={completed}, "
          f"upcoming={len(wc_matches) - completed}) players={len(squads)}")


if __name__ == "__main__":
    main()
