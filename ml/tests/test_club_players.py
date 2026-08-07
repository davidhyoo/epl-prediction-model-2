"""
Unit tests for ``club_players.build_players`` — the roster + goal-stat merge.

These lock down the behaviours that make Champions-League (and domestic) player
stats correct despite the app using each club's *current* squad:

  * exact-name goals win over a shared surname (no stolen tallies),
  * a real scorer absent from the squad still appears (orphan record),
  * an ``injected`` goal_stats map (the UCL source) is consumed verbatim, and
  * a transferred player isn't listed twice (0-goal roster copy de-duped), while
    two different players who merely share a name are both kept.

Pure computation — no network, no trained artifacts.
"""
from club_players import build_players


def _sq(pid, name, pos="FWD", **extra):
    """A minimal squad-member record shaped like club_fetch_squads output."""
    rec = {
        "id": pid, "name": name, "position": pos,
        "detailedPosition": {"GK": "Goalkeeper", "DEF": "Defender",
                             "MID": "Midfielder", "FWD": "Forward"}[pos],
        "wiki": name, "clubName": None, "shirtNumber": 9,
        "nationIso2": None, "nationName": None,
        "headshot": None, "photoCredit": None,
    }
    rec.update(extra)
    return rec


STRENGTH = {"BVB": {"overall": 70.0}, "BAR": {"overall": 80.0},
            "INT": {"overall": 75.0}, "NEW": {"overall": 60.0}}


def _players_by_name(result):
    return {p["name"]: p for p in result["players"]}


def test_injected_goal_stats_are_consumed_verbatim():
    squads = {"BVB": [_sq("BVB-9", "Serhou Guirassy")]}
    goal_stats = {
        ("BVB", "serhou guirassy"): {
            "goals": 13, "penalties": 0, "minutes": [], "minutesPlayed": 1084,
            "nationIso2": "gn", "nationName": "Guinea", "display": "Serhou Guirassy",
        }
    }
    res = build_players("ucl", "2024-25", squads, STRENGTH, [], goal_stats=goal_stats)
    p = _players_by_name(res)["Serhou Guirassy"]
    assert p["goals"] == 13
    assert p["minutes"] == 1084          # real UEFA minutes threaded through
    assert p["rating"] > 50              # a 13-goal FWD outranks the positional prior
    assert res["topScorers"] == ["BVB-9"]


def test_exact_match_beats_shared_surname():
    # A GK named "Josep Martínez" must NOT inherit "Lautaro Martínez"'s goals.
    squads = {
        "INT": [
            _sq("INT-1", "Josep Martínez", pos="GK"),
            _sq("INT-10", "Lautaro Martínez", pos="FWD"),
        ]
    }
    goal_stats = {
        ("INT", "lautaro martinez"): {
            "goals": 9, "penalties": 1, "minutes": [], "minutesPlayed": 900,
            "display": "Lautaro Martínez",
        }
    }
    res = build_players("ucl", "2024-25", squads, STRENGTH, [], goal_stats=goal_stats)
    by = _players_by_name(res)
    assert by["Lautaro Martínez"]["goals"] == 9
    assert by["Josep Martínez"]["goals"] == 0


def test_unrostered_scorer_becomes_orphan_with_nationality():
    # A real scorer who is not in the current squad still appears (departed star).
    squads = {"BAR": [_sq("BAR-1", "Marc-André ter Stegen", pos="GK")]}
    goal_stats = {
        ("BAR", "robert lewandowski"): {
            "goals": 11, "penalties": 2, "minutes": [], "minutesPlayed": 985,
            "nationIso2": "pl", "nationName": "Poland", "display": "Robert Lewandowski",
        }
    }
    res = build_players("ucl", "2024-25", squads, STRENGTH, [], goal_stats=goal_stats)
    by = _players_by_name(res)
    lewa = by["Robert Lewandowski"]
    assert lewa["goals"] == 11
    assert "-x-" in lewa["id"]            # orphan record id marker
    assert lewa["nationName"] == "Poland"
    assert lewa["club"] == "BAR"


def test_transfer_dedupe_drops_zero_goal_roster_copy():
    # Anthony Gordon scored for NEW but now sits in BAR's current squad with 0
    # goals: keep the goalscoring (orphan) record, drop the 0-goal roster copy.
    squads = {
        "NEW": [_sq("NEW-7", "Bruno Guimarães", pos="MID")],
        "BAR": [_sq("BAR-11", "Anthony Gordon", pos="FWD")],
    }
    goal_stats = {
        ("NEW", "anthony gordon"): {
            "goals": 10, "penalties": 0, "minutes": [], "minutesPlayed": 900,
            "nationName": "England", "display": "Anthony Gordon",
        }
    }
    res = build_players("ucl", "2025-26", squads, STRENGTH, [], goal_stats=goal_stats)
    gordons = [p for p in res["players"] if p["name"] == "Anthony Gordon"]
    assert len(gordons) == 1
    assert gordons[0]["goals"] == 10
    assert gordons[0]["club"] == "NEW"


def test_dedupe_keeps_two_distinct_players_with_the_same_name():
    # Two real, different "Nico González" (no orphan): both must survive.
    squads = {
        "BAR": [_sq("MCI-16", "Nico González", pos="MID")],
        "INT": [_sq("JUV-28", "Nico González", pos="FWD")],
    }
    res = build_players("ucl", "2025-26", squads, STRENGTH, [], goal_stats={})
    nicos = [p for p in res["players"] if p["name"] == "Nico González"]
    assert len(nicos) == 2
