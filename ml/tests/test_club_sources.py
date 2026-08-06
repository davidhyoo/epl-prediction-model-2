"""
Unit tests for the cached-source parsers (``club_sources``).

Pure text parsing, no network. Covers the three openfootball line layouts
(newer score, older ``v`` score, fixture-only), the goalscorer grammar
(penalties, own goals, stoppage-time minutes, multi-goal players) and the
football-data.co.uk CSV parser (per-match stats + normalised market odds).
"""
import pytest

from club_sources import (
    parse_fd_history,
    parse_football_data,
    parse_openfootball,
)

# --------------------------------------------------------------------------- #
# openfootball — newer layout with an inline scorer block
# --------------------------------------------------------------------------- #
NEW_FORMAT = """\
= English Premier League 2025/26

» Matchday 1

Sat Aug 16 2025
 12:30  Arsenal  2-1 (1-0)  Chelsea
    (Saka 12' (p), Odegaard 66'; Palmer 88')
 15:00  Liverpool  3-3 (2-1)  Manchester City
    (Salah 5', 40', Nunez 77'; Haaland 20', Foden 60', 90+2' (og))
"""


def test_parse_openfootball_new_format_scores():
    matches = parse_openfootball(NEW_FORMAT, "epl")
    assert len(matches) == 2
    m = matches[0]
    assert (m["home"], m["away"]) == ("ARS", "CHE")
    assert (m["homeGoals"], m["awayGoals"]) == (2, 1)
    assert (m["htHome"], m["htAway"]) == (1, 0)
    assert m["round"] == 1
    assert m["date"] == "2025-08-16"


def test_parse_openfootball_penalty_flag_and_minutes():
    m = parse_openfootball(NEW_FORMAT, "epl")[0]
    saka = next(s for s in m["scorers"] if s["player"] == "Saka")
    assert saka["penalty"] is True
    assert saka["minute"] == 12
    assert saka["scorerTeam"] == "ARS"


def test_parse_openfootball_multi_goal_and_stoppage_and_own_goal():
    m = parse_openfootball(NEW_FORMAT, "epl")[1]
    salah_goals = [s for s in m["scorers"] if s["player"] == "Salah"]
    assert len(salah_goals) == 2  # 5' and 40'
    # An own goal is credited to the beneficiary team but NOT to the named player.
    og = next(s for s in m["scorers"] if s["ownGoal"])
    assert og["stoppage"] == 2 and og["minute"] == 90
    assert og["forTeam"] == "MCI"      # listed under Man City's tally
    assert og["scorerTeam"] == "LIV"   # but the player plays for Liverpool


# --------------------------------------------------------------------------- #
# openfootball — older "v" layouts
# --------------------------------------------------------------------------- #
OLD_FORMAT = """\
Sat Aug 16 2025
  Arsenal v Chelsea  2-1 (1-0)
  Liverpool v Manchester City  0-0
"""

FIXTURE_ONLY = """\
Sat Aug 15 2026
 20:00  Arsenal v Chelsea
 17:30  Liverpool v Manchester City
"""


def test_parse_openfootball_old_v_score_format():
    matches = parse_openfootball(OLD_FORMAT, "epl")
    assert len(matches) == 2
    assert (matches[0]["homeGoals"], matches[0]["awayGoals"]) == (2, 1)
    assert (matches[1]["homeGoals"], matches[1]["awayGoals"]) == (0, 0)


def test_parse_openfootball_fixture_only_has_no_score():
    matches = parse_openfootball(FIXTURE_ONLY, "epl")
    assert len(matches) == 2
    for m in matches:
        assert m["homeGoals"] is None
        assert m["awayGoals"] is None
        assert m["scorers"] == []
    assert matches[0]["datetime"].endswith("20:00:00+00:00")


def test_parse_openfootball_skips_unknown_clubs():
    text = "Sat Aug 16 2025\n 15:00  Arsenal  1-0  Notarealclub FC\n"
    assert parse_openfootball(text, "epl") == []


# --------------------------------------------------------------------------- #
# football-data.co.uk CSV
# --------------------------------------------------------------------------- #
FD_CSV = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,HS,AS,HST,AST,HC,AC,HF,AF,"
    "HY,AY,HR,AR,Referee,AvgH,AvgD,AvgA\r\n"
    "E0,16/08/2025,Arsenal,Chelsea,2,1,15,9,7,4,6,3,10,12,1,2,0,0,M Oliver,"
    "1.80,3.60,4.50\r\n"
    "E0,17/08/2025,Liverpool,Man City,3,3,14,13,6,6,5,7,8,9,2,1,0,0,A Taylor,"
    "2.10,3.50,3.30\r\n"
)


def test_parse_football_data_merges_stats_and_odds():
    out = parse_football_data(FD_CSV, "epl")
    stats = out[("ARS", "CHE")]
    assert stats["shotsOnTarget"] == {"home": 7, "away": 4}
    assert stats["corners"] == {"home": 6, "away": 3}
    assert stats["referee"] == "M Oliver"


def test_parse_football_data_odds_are_normalised_probabilities():
    out = parse_football_data(FD_CSV, "epl")
    odds = out[("ARS", "CHE")]["marketOdds"]
    assert set(odds) == {"home", "draw", "away"}
    assert sum(odds.values()) == pytest.approx(1.0, abs=1e-3)
    # Favourite (lowest decimal odds) carries the highest implied probability.
    assert odds["home"] > odds["away"]


def test_parse_fd_history_returns_only_completed_rows():
    rows = parse_fd_history(FD_CSV, "epl")
    assert len(rows) == 2
    assert all(r["homeGoals"] is not None for r in rows)
    # "Man City" is a loose alias for Manchester City.
    assert rows[1]["away"] == "MCI"
