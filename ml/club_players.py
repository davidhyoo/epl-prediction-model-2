"""
club_players.py  —  stage 7: player roster + real goal stats
============================================================
Combines two real, free data sources into one player record per squad member:

  * **who** — the club's current first-team squad (name, shirt number, position,
    nationality, free-licensed headshot) from ``club_fetch_squads`` (Wikipedia).
  * **what they did** — goals + penalties + goal minutes aggregated from the
    openfootball inline goalscorers of the target season (CC0, real per-match
    scorers).

Goals are matched to squad players by an accent-folded name key, with a surname
fallback. A real scorer who isn't in the parsed squad (e.g. a since-departed
player) is still added so the league's true top scorers always appear. Stats we
have no free per-player source for (assists, minutes, cards) are left ``null`` and
the UI renders a tasteful "—"; the app never invents them.

A transparent 0–100 **rating** blends the player's goal output with their club's
strength and a small positional prior — clearly a derived score, not a claimed
official metric.
"""
from __future__ import annotations

import numpy as np

from leagues import normalize_name

POS_BASE = {"GK": 46.0, "DEF": 50.0, "MID": 53.0, "FWD": 56.0}


def _name_key(name: str) -> str:
    return normalize_name(name)


def _surname_key(name: str) -> str:
    parts = normalize_name(name).split()
    return parts[-1] if parts else ""


def aggregate_goals(matches: list[dict]) -> dict[str, dict]:
    """(clubCode, name-key) -> {goals, penalties, minutes[]} from real scorers."""
    agg: dict[tuple[str, str], dict] = {}
    for m in matches:
        if m.get("status") != "completed":
            continue
        for ev in m.get("scorers") or []:
            if ev.get("ownGoal"):
                continue  # own goals are not credited to the player
            club = ev.get("scorerTeam")
            key = _name_key(ev.get("player", ""))
            if not club or not key:
                continue
            rec = agg.setdefault((club, key), {
                "goals": 0, "penalties": 0, "minutes": [],
                "display": ev.get("player", "").title()})
            rec["goals"] += 1
            if ev.get("penalty"):
                rec["penalties"] += 1
            rec["minutes"].append(ev.get("minuteLabel"))
    return agg


def build_players(league_id: str, season_id: str, squads: dict,
                  strength: dict, matches: list[dict]) -> dict:
    """Return {'players': [...], 'topScorers': [...]} for one combo."""
    goals = aggregate_goals(matches)

    # index real-goal records by club so we can spot un-rostered scorers
    by_club: dict[str, dict[str, dict]] = {}
    for (club, key), rec in goals.items():
        by_club.setdefault(club, {})[key] = rec

    players: list[dict] = []
    used: set[tuple[str, str]] = set()

    for club_code, roster in squads.items():
        club_goals = by_club.get(club_code, {})
        surname_idx: dict[str, str] = {}
        for k in club_goals:
            surname_idx.setdefault(k.split()[-1] if k.split() else k, k)

        for p in roster:
            key = _name_key(p["name"])
            rec = club_goals.get(key)
            if rec is None:
                sk = _surname_key(p["name"])
                mk = surname_idx.get(sk)
                if mk and (club_code, mk) not in used:
                    rec = club_goals.get(mk)
                    key = mk
            g = rec["goals"] if rec else 0
            pens = rec["penalties"] if rec else 0
            mins = rec["minutes"] if rec else []
            if rec:
                used.add((club_code, key))
            players.append(_finalize(club_code, p, g, pens, mins, strength))

        # real scorers not matched to a rostered player (departed / parse gaps)
        for key, rec in club_goals.items():
            if (club_code, key) in used:
                continue
            players.append(_orphan_scorer(club_code, rec, strength))
            used.add((club_code, key))

    _rank_ratings(players)
    top = sorted([p for p in players if p["goals"] > 0],
                 key=lambda p: (-p["goals"], -p["penalties"], p["name"]))[:25]
    for i, p in enumerate(top):
        p["scorerRank"] = i + 1
    return {"players": players, "topScorers": [t["id"] for t in top]}


def _finalize(club_code: str, p: dict, goals: int, pens: int,
              minutes: list, strength: dict) -> dict:
    st = strength.get(club_code, {})
    return {
        "id": p["id"], "name": p["name"], "wiki": p.get("wiki"),
        "club": club_code, "clubName": p.get("clubName"),
        "position": p["position"], "detailedPosition": p["detailedPosition"],
        "shirtNumber": p.get("shirtNumber") or 0,
        "nationIso2": p.get("nationIso2"), "nationName": p.get("nationName"),
        "headshot": p.get("headshot"), "photoCredit": p.get("photoCredit"),
        "goals": goals, "penalties": pens, "goalMinutes": minutes,
        "assists": None, "appearances": None, "minutes": None,
        "yellowCards": None, "redCards": None,
        "clubStrength": st.get("overall", 50.0),
        "rating": 0.0,  # filled by _rank_ratings
    }


def _orphan_scorer(club_code: str, rec: dict, strength: dict) -> dict:
    st = strength.get(club_code, {})
    name = rec["display"]
    return {
        "id": f"{club_code}-x-{normalize_name(name).replace(' ', '-')}",
        "name": name, "wiki": name, "club": club_code,
        "clubName": None, "position": "FWD", "detailedPosition": "Forward",
        "shirtNumber": 0, "nationIso2": None, "nationName": None,
        "headshot": None, "photoCredit": None,
        "goals": rec["goals"], "penalties": rec["penalties"],
        "goalMinutes": rec["minutes"], "assists": None, "appearances": None,
        "minutes": None, "yellowCards": None, "redCards": None,
        "clubStrength": st.get("overall", 50.0), "rating": 0.0,
    }


def _rank_ratings(players: list[dict]) -> None:
    """Derived 0–100 rating: positional prior + club strength + goal output."""
    if not players:
        return
    goals = np.array([p["goals"] for p in players], dtype=float)
    gmax = goals.max() or 1.0
    for p in players:
        base = POS_BASE.get(p["position"], 50.0)
        club_term = 0.18 * (p["clubStrength"] - 50.0)
        goal_term = 34.0 * (p["goals"] / gmax) ** 0.65
        p["rating"] = round(float(np.clip(base + club_term + goal_term, 30.0, 99.0)), 1)
