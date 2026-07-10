"""
ingest.py  —  Stage 1: raw data ingestion
=========================================
Builds the raw, reproducible inputs for the pipeline:

  * teams (48) + a pot-based group draw + latent "true" strengths
  * a synthetic history of international matches 2019-2025 (TRAINING data)
  * the single canonical 2026 World Cup bracket with "actual" results
    (group stage completed; knockout stage upcoming)
  * base squads (26 generated players per team)

Everything is seeded so re-running produces identical output. The latent
strengths are the data-generating process; Elo/form features (built later in
features.py) only ever *estimate* them from observed results — so the models
never see the ground truth (no leakage).
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np

from common import (
    load_teams, rng, GROUP_START, VENUES, GROUPS, HOME_ADV,
    NAME_CULTURE, FIRST_NAMES, LAST_NAMES, BIG_CLUBS, MID_CLUBS, SMALL_CLUBS,
    POSITION_DETAIL, RAW_DIR, write_json_pretty, scale_0_100,
)
from tournament import (
    draw_groups, play_match, blank_record, apply_result, group_tables,
    qualified_ranked, r32_bracket_positions,
)
import os

# --------------------------------------------------------------------------- #
# Latent strengths (ground truth for the data-generating process)
# --------------------------------------------------------------------------- #
def assign_latent(teams) -> dict[str, float]:
    r = rng("latent")
    latent = {}
    for t in teams:
        latent[t.code] = t.elo0 + float(r.normal(0, 22))
    return latent


# --------------------------------------------------------------------------- #
# Historical international matches (training set)
# --------------------------------------------------------------------------- #
def generate_history(teams, latent) -> list[dict]:
    r = rng("history")
    codes = [t.code for t in teams]
    matches: list[dict] = []
    start = GROUP_START.replace(year=2019, month=3, day=1)
    n_rounds = 175  # ~175 * 24 = 4200 matches
    mid = 0
    for rd in range(n_rounds):
        order = codes.copy()
        r.shuffle(order)
        date = start + timedelta(days=rd * 14 + int(r.integers(0, 5)))
        for i in range(0, len(order), 2):
            a, b = order[i], order[i + 1]
            # designate home advantage (home-field) for team A with prob 0.6
            home_field = r.random() < 0.6
            bonus = HOME_ADV if home_field else 0.0
            res = play_match(latent[a] + bonus, latent[b], r, knockout=False)
            matches.append({
                "id": f"H{mid:05d}",
                "date": date.isoformat(),
                "home": a, "away": b,
                "home_adv": 1 if home_field else 0,
                "gh": res["ga"], "ga": res["gb"],
                "stage": "friendly",
            })
            mid += 1
    return matches


# --------------------------------------------------------------------------- #
# World Cup fixtures + canonical simulation
# --------------------------------------------------------------------------- #
GROUP_ROUNDS = [((0, 3), (1, 2)), ((0, 2), (3, 1)), ((0, 1), (2, 3))]


def _orient(a_team, b_team):
    """Put a host nation as the nominal home side (gets home advantage)."""
    if b_team.host and not a_team.host:
        return b_team, a_team
    return a_team, b_team


def generate_world_cup(teams, latent) -> list[dict]:
    r = rng("worldcup")
    by_code = {t.code: t for t in teams}
    records = {t.code: blank_record() for t in teams}
    matches: list[dict] = []
    venue_i = 0

    def next_venue():
        nonlocal venue_i
        v = VENUES[venue_i % len(VENUES)]
        venue_i += 1
        return v

    # ---- Group stage (72 matches) ----------------------------------------
    mid = 0
    for gi, g in enumerate(GROUPS):
        members = [t for t in teams if t.group == g]
        members.sort(key=lambda t: -t.elo0)  # stable order within group
        for md, rounds in enumerate(GROUP_ROUNDS):
            for (ia, ib) in rounds:
                a_team, b_team = _orient(members[ia], members[ib])
                home_adv = 1 if a_team.host else 0
                bonus = HOME_ADV if home_adv else 0.0
                res = play_match(latent[a_team.code] + bonus, latent[b_team.code],
                                 r, knockout=False)
                gh, ga = res["ga"], res["gb"]
                apply_result(records[a_team.code], gh, ga)
                apply_result(records[b_team.code], ga, gh)
                venue, city = next_venue()
                date = GROUP_START + timedelta(days=md * 5 + gi % 6,
                                               hours=12 + (gi % 3) * 3)
                matches.append({
                    "id": f"G{mid:03d}",
                    "stage": "group", "group": g, "matchday": md + 1,
                    "slot": gi * 3 + md,
                    "date": date.isoformat(), "venue": venue, "city": city,
                    "home": a_team.code, "away": b_team.code,
                    "home_adv": home_adv,
                    "gh": gh, "ga": ga, "pens": None, "winner": res["winner"],
                })
                mid += 1

    tables = group_tables(records, by_code)
    ranked = qualified_ranked(tables, records, by_code)
    positions = r32_bracket_positions(ranked)  # 32 codes in bracket order

    # ---- Knockout stage ---------------------------------------------------
    def knockout_round(codes_in_positions, stage, label_base, start_day, count):
        """Play a knockout round; return winners (in bracket order) + append matches."""
        winners = []
        losers = []
        for slot in range(count):
            a = codes_in_positions[slot * 2]
            b = codes_in_positions[slot * 2 + 1]
            a_team, b_team = by_code[a], by_code[b]
            bonus_a = HOME_ADV * 0.6 if a_team.host else 0.0
            bonus_b = HOME_ADV * 0.6 if b_team.host else 0.0
            res = play_match(latent[a] + bonus_a, latent[b] + bonus_b, r, knockout=True)
            winner = a if res["winner"] == "A" else b
            loser = b if winner == a else a
            winners.append(winner)
            losers.append(loser)
            venue, city = next_venue()
            date = GROUP_START + timedelta(days=start_day + slot // 2)
            matches.append({
                "id": f"{stage_code(stage)}{slot:02d}",
                "stage": stage, "group": None, "slot": slot,
                "date": date.isoformat(), "venue": venue, "city": city,
                "home": a, "away": b, "home_adv": 1 if bonus_a > 0 else 0,
                "gh": res["ga"], "ga": res["gb"], "pens": res["pens"],
                "winner": "A" if winner == a else "B",
            })
        return winners, losers

    def stage_code(stage):
        return {"round-of-32": "R32", "round-of-16": "R16", "quarter-final": "QF",
                "semi-final": "SF", "third-place": "TP", "final": "FN"}[stage]

    r32_w, _ = knockout_round(positions, "round-of-32", "R32", 17, 16)
    r16_w, _ = knockout_round(r32_w, "round-of-16", "R16", 23, 8)
    qf_w, _ = knockout_round(r16_w, "quarter-final", "QF", 28, 4)
    sf_w, sf_l = knockout_round(qf_w, "semi-final", "SF", 33, 2)
    # third place
    knockout_round(sf_l, "third-place", "TP", 37, 1)
    knockout_round(sf_w, "final", "FN", 38, 1)

    return matches, records, tables, ranked, positions


# --------------------------------------------------------------------------- #
# Squad generation (synthetic demo players)
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
    # fallback with suffix
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
        # role ratings around team base
        team_base = base[t.code]
        # assign shirt numbers
        shirts = list(range(1, 27))
        # ratings: create a descending distribution with a few stars
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
        # shirt numbers: sort GK first
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
        # captain = highest-rated outfield
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
    draw_groups(teams)
    latent = assign_latent(teams)

    history = generate_history(teams, latent)
    wc_matches, records, tables, ranked, positions = generate_world_cup(teams, latent)
    squads = generate_squads(teams)

    teams_raw = []
    for t in teams:
        teams_raw.append({
            "code": t.code, "iso2": t.iso2, "name": t.name,
            "confederation": t.confederation, "group": t.group, "pot": t.pot,
            "elo0": t.elo0, "fifaRank": t.fifa_rank, "host": t.host,
            "colors": {"primary": t.primary, "secondary": t.secondary},
            "latent": round(latent[t.code], 1),
        })

    write_json_pretty(os.path.join(RAW_DIR, "teams.json"), teams_raw)
    write_json_pretty(os.path.join(RAW_DIR, "history.json"), history)
    write_json_pretty(os.path.join(RAW_DIR, "wc_matches.json"), wc_matches)
    write_json_pretty(os.path.join(RAW_DIR, "squads.json"), squads)
    write_json_pretty(os.path.join(RAW_DIR, "qualification.json"), {
        "tables": tables,
        "ranked32": ranked,
        "bracketPositions": positions,
        "records": records,
    })

    print(f"[ingest] teams={len(teams_raw)} history={len(history)} "
          f"wc_matches={len(wc_matches)} players={len(squads)}")


if __name__ == "__main__":
    main()
