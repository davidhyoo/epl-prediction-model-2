"""
Unit tests for ``ucl_stats`` — the Champions-League per-player goal source.

openfootball's UCL feed has no goalscorer annotations, so real UCL player goals
come from the free Wikipedia/UEFA "Top goalscorers" wikitable. These tests lock
down the wikitable parser (rowspan carry-forward for shared tallies, the
player-vs-team ``flagicon``/``fbaicon`` discriminator, minutes, nationality) and
the ``load_goal_stats`` cache reader — all pure/offline, no network.
"""
import json

import ucl_stats


# --------------------------------------------------------------------------- #
# Nationality flag extraction
# --------------------------------------------------------------------------- #
def test_flag_code_extracts_iso3():
    assert ucl_stats._flag_code("{{flagicon|GUI}} [[Serhou Guirassy]]") == "GUI"
    assert ucl_stats._flag_code("{{flagicon|BRA}} [[Raphinha]]") == "BRA"
    # a team cell (fbaicon) is NOT a player nationality flag
    assert ucl_stats._flag_code("{{fbaicon|ESP}} [[FC Barcelona]]") is None
    assert ucl_stats._flag_code("no template here") is None


# --------------------------------------------------------------------------- #
# Wikitable parsing
# --------------------------------------------------------------------------- #
# A faithful miniature of the real "Top goalscorers" table: Rank + Goals use
# rowspan (continuation rows omit them), the player cell carries {{flagicon}} and
# the team cell {{fbaicon}}, and the trailing columns are Goals then Minutes.
SAMPLE_TABLE = """{| class="wikitable"
|-
! Rank !! Player !! Team !! Goals !! Minutes
|-
| rowspan="2" | 1 || {{flagicon|GUI}} [[Serhou Guirassy]] || {{fbaicon|GER}} [[Borussia Dortmund]] || rowspan="2" | 13 || 1084
|-
| {{flagicon|BRA}} [[Raphinha]] || {{fbaicon|ESP}} [[FC Barcelona]] || 1225
|-
| 3 || {{flagicon|POL}} [[Robert Lewandowski]] || {{fbaicon|ESP}} [[FC Barcelona]] || 11 || 985
|}"""


def test_parse_topscorers_rowspan_and_columns():
    rows = ucl_stats.parse_topscorers(SAMPLE_TABLE)
    assert len(rows) == 3

    guirassy, raphinha, lewa = rows
    assert guirassy["player"] == "Serhou Guirassy"
    assert guirassy["team"] == "Borussia Dortmund"
    assert guirassy["goals"] == 13
    assert guirassy["minutes"] == 1084
    assert guirassy["nation"] == "GUI"

    # continuation row inherits the shared "13" goals via rowspan carry-forward
    assert raphinha["player"] == "Raphinha"
    assert raphinha["goals"] == 13
    assert raphinha["minutes"] == 1225
    assert raphinha["nation"] == "BRA"

    assert lewa["player"] == "Robert Lewandowski"
    assert lewa["goals"] == 11
    assert lewa["nation"] == "POL"


def test_parse_topscorers_skips_summary_rows():
    # A "Seven players" style summary row has no wikilinks / templates and must
    # not become a phantom scorer.
    table = """{| class="wikitable"
|-
! Rank !! Player !! Team !! Goals !! Minutes
|-
| 1 || {{flagicon|FRA}} [[Kylian Mbappé]] || {{fbaicon|ESP}} [[Real Madrid]] || 15 || 1200
|-
| colspan="2" | Seven players || 6 ||
|}"""
    rows = ucl_stats.parse_topscorers(table)
    assert [r["player"] for r in rows] == ["Kylian Mbappé"]


# --------------------------------------------------------------------------- #
# Cache reader shape (offline)
# --------------------------------------------------------------------------- #
def test_load_goal_stats_shape(tmp_path, monkeypatch):
    season = "2024-25"
    cache = {
        "season": season,
        "source": "wikipedia/uefa",
        "scorers": [
            {"player": "Serhou Guirassy", "club": "BVB", "goals": 13,
             "minutes": 1084, "nationIso2": "gn", "nationName": "Guinea"},
        ],
    }
    path = tmp_path / "topscorers.json"
    path.write_text(json.dumps(cache), encoding="utf-8")
    monkeypatch.setattr(ucl_stats, "_cache_path", lambda sid: str(path))

    stats = ucl_stats.load_goal_stats(season)
    key = ("BVB", "serhou guirassy")
    assert key in stats
    rec = stats[key]
    assert rec["goals"] == 13
    assert rec["minutesPlayed"] == 1084
    assert rec["penalties"] == 0          # UEFA table has no penalty split
    assert rec["minutes"] == []           # no per-goal minute labels for the UCL
    assert rec["nationIso2"] == "gn"
    assert rec["nationName"] == "Guinea"
    assert rec["display"] == "Serhou Guirassy"


def test_load_goal_stats_missing_cache_returns_empty(monkeypatch):
    monkeypatch.setattr(ucl_stats, "_cache_path", lambda sid: "/no/such/file.json")
    assert ucl_stats.load_goal_stats("2024-25") == {}
