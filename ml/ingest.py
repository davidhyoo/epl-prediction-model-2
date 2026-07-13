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
  * squads          — the real, current 26-player squad for each nation, parsed
                      from the maintained Wikipedia "national football team"
                      squad templates by ml/fetch_players.py (names, shirt no.,
                      position, age, caps, goals, club + a free-licensed headshot
                      where one exists on Wikimedia Commons). Player *ratings* and
                      per-tournament *statistics* remain model-generated (no free
                      source exists) and are clearly flagged as such. Falls back
                      to fully generated squads if the cache is unavailable.

No World Cup match is ever used for training (leakage-free): history stops the
day before the opener.
"""
from __future__ import annotations

import math
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
# Real squads (Wikipedia, cached by ml/fetch_players.py) with synthesised
# player ratings. Wikipedia gives us verified identities (name, position, age,
# caps, goals, club, headshot) but no ability rating, so we derive a transparent,
# deterministic rating from the nation's strength + the player's role, caps and
# goals. Ratings/statistics are always labelled model-generated in the UI.
# --------------------------------------------------------------------------- #
_ROLE_BONUS = {"GK": -1.0, "DEF": -0.5, "MID": 0.4, "FWD": 0.6}


def _synth_rating(team_base: float, pos: str, caps, goals, is_captain: bool, gen) -> float:
    rating = team_base + _ROLE_BONUS[pos]
    # International experience, centred so ~20 caps is neutral: fringe players sit
    # below their nation's base, seasoned internationals above it (keeps a real
    # spread instead of everyone piling on the ceiling).
    rating += (math.log1p(caps or 0) - 3.2) * 1.5
    if pos == "FWD":
        rating += min(goals or 0, 60) * 0.06              # proven goalscorers
    if is_captain:
        rating += 1.0                                     # first-choice leaders
    rating += gen.normal(0.0, 1.1)                        # per-player variation
    return round(float(np.clip(rating, 50, 95)), 1)


def _real_row(src: dict, team_base: float, gen, stats_map: dict) -> dict:
    pos = src["position"]
    age = src.get("age")
    wiki = src.get("wiki")
    return {
        "id": src["id"],
        "name": src["name"],
        "countryCode": src["countryCode"],
        "country": src["country"],
        "iso2": src["iso2"],
        "position": pos,
        "detailedPosition": src.get("detailedPosition") or pos.title(),
        "age": int(age) if isinstance(age, (int, float)) else None,
        "club": src.get("club"),
        "clubCountry": src.get("clubCountry"),
        "rating": _synth_rating(team_base, pos, src.get("caps"), src.get("intlGoals"),
                                bool(src.get("isCaptain")), gen),
        "isCaptain": bool(src.get("isCaptain")),
        "shirtNumber": src.get("shirtNumber") or 0,
        "caps": src.get("caps"),
        "intlGoals": src.get("intlGoals"),
        "headshot": src.get("headshot"),
        "photoCredit": src.get("photoCredit"),
        "wiki": wiki,
        # Real WC-2026 tournament stats joined by exact Wikipedia title (or None
        # when the player has not featured yet → real zeros downstream).
        "realStats": stats_map.get(S.norm_wiki_title(wiki)) if wiki else None,
        "real": True,
    }


def _fill_team(team, team_base: float, gen, start: int, need: int) -> list[dict]:
    """Generate ``need`` placeholder players (real=False) to top up a short or
    missing squad, so downstream size expectations stay satisfied even if a
    nation's Wikipedia squad could not be parsed."""
    culture = NAME_CULTURE.get(team.code, "english")
    used: set = set()
    fill_pos = (["DEF", "MID", "FWD", "DEF", "MID", "GK"] * 6)[:need]
    out: list[dict] = []
    for k, pos in enumerate(fill_pos):
        rating = float(np.clip(team_base + _pos_bias(pos, gen), 55, 90))
        club, club_country = pick_club(rating, gen)
        detail = POSITION_DETAIL[pos][int(gen.integers(0, len(POSITION_DETAIL[pos])))]
        out.append({
            "id": f"{team.code}-{start + k + 1:02d}",
            "name": unique_name(culture, used, gen),
            "countryCode": team.code, "country": team.name, "iso2": team.iso2,
            "position": pos, "detailedPosition": detail,
            "age": int(np.clip(gen.normal(26.5, 3.6), 18, 39)),
            "club": club, "clubCountry": club_country,
            "rating": round(rating, 1), "isCaptain": False, "shirtNumber": 0,
            "caps": None, "intlGoals": None,
            "headshot": None, "photoCredit": None,
            "wiki": None, "realStats": None, "real": False,
        })
    return out


def build_squads(teams) -> list[dict]:
    """Real squads from the Wikipedia cache (see ml/fetch_players.py), with a
    deterministic generated fallback when the cache is missing/unreadable."""
    real = S.load_squads()
    if not real:
        players = generate_squads(teams)
        for p in players:  # keep the frontend contract uniform
            p.update(real=False, caps=None, intlGoals=None, headshot=None,
                     photoCredit=None, wiki=None, realStats=None)
        return players

    stats_map = S.load_player_stats() or {}
    base = team_base_rating(teams)
    gen = rng("real-ratings")
    players: list[dict] = []
    for t in teams:
        rows = [r for r in (real.get(t.code) or [])
                if r.get("position") in ("GK", "DEF", "MID", "FWD") and r.get("name")]
        if len(rows) >= 18:
            team_players = [_real_row(r, base[t.code], gen, stats_map) for r in rows[:26]]
            if len(team_players) < 23:  # rare short squad → top up with fillers
                team_players += _fill_team(t, base[t.code], gen,
                                           start=len(team_players), need=23 - len(team_players))
        else:                            # unparsed nation → fully generated squad
            team_players = _fill_team(t, base[t.code], gen, start=0, need=26)
        players.extend(team_players)
    return players


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    teams = load_teams()

    history = build_history()
    (wc_matches, records, tables, ranked32,
     bracket_positions, knockout_tree) = build_world_cup(teams)
    squads = build_squads(teams)

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
    real_players = sum(1 for p in squads if p.get("real"))
    print(f"[ingest] teams={len(teams_raw)} history={len(history)} "
          f"wc_matches={len(wc_matches)} (completed={completed}, "
          f"upcoming={len(wc_matches) - completed}) players={len(squads)} "
          f"(real={real_players}, generated={len(squads) - real_players})")


if __name__ == "__main__":
    main()
