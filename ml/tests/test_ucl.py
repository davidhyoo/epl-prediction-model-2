"""
Unit tests for the Champions-League (tournament-format) pipeline pieces.

Covers the openfootball UCL parser (stage headers, score tails with extra time /
penalties, league-vs-knockout round numbering) and the knockout-bracket
championship model (bracket reconstruction, a decided champion, a normalised
odds distribution and a convergence timeline). Pure computation — no network,
no trained artifacts — so the suite stays sub-second.
"""
import pytest

from club_sources import (
    _parse_ucl_score,
    _ucl_stage,
    parse_openfootball_ucl,
)
from ucl_bracket import build_tree, championship, preseason_odds


# --------------------------------------------------------------------------- #
# Stage-header mapping
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "header, stage, matchday",
    [
        ("▪ League, Matchday 1", "league", 1),
        ("▪ League, Matchday 8", "league", 8),
        ("▪ Playoffs, Matchday 1", "playoff", 1),
        ("▪ Playoffs, Matchday 2", "playoff", 2),
        ("▪ Finals, Round of 16", "r16", None),
        ("▪ Finals, Quarterfinals", "qf", None),
        ("▪ Finals, Semifinals", "sf", None),
        ("▪ Finals, Final", "final", None),
        ("▪ Group A", "league", 0),  # pre-2024 group-stage layout
    ],
)
def test_ucl_stage_headers(header, stage, matchday):
    assert _ucl_stage(header) == (stage, matchday)


# --------------------------------------------------------------------------- #
# Score-tail parsing
# --------------------------------------------------------------------------- #
def test_ucl_score_normal_and_empty():
    assert _parse_ucl_score("3-1 (2-0)") == (3, 1, None)
    assert _parse_ucl_score("0-0") == (0, 0, None)
    assert _parse_ucl_score("") == (None, None, None)


def test_ucl_score_extra_time_uses_on_pitch_result():
    # Extra-time result with no shootout: the leading number pair is the result.
    assert _parse_ucl_score("0-1 a.e.t. (0-1, 0-1)") == (0, 1, None)


def test_ucl_score_penalty_shootout():
    # "1-4 pen. 0-1 a.e.t." → shootout 1-4, on-pitch (a.e.t.) result 0-1.
    hg, ag, pens = _parse_ucl_score("1-4 pen. 0-1 a.e.t. (0-1, 0-1)")
    assert (hg, ag) == (0, 1)
    assert pens == (1, 4)


# --------------------------------------------------------------------------- #
# End-to-end parse of a multi-stage sample
# --------------------------------------------------------------------------- #
SAMPLE = """\
= UEFA Champions League 2024/25

▪ League, Matchday 1
  Tue Sep 17 2024
    21:00  Real Madrid CF (ESP)    v Aston Villa FC (ENG)     3-1 (0-0)
           FC Bayern München (GER) v FC Barcelona (ESP)       2-2 (1-1)

▪ Finals, Round of 16
  Tue Mar 4 2025
    21:00  FC Barcelona (ESP)      v Real Madrid CF (ESP)     2-1 (1-0)

▪ Finals, Final
  Sat May 31 2025
    21:00  Liverpool FC (ENG)      v Paris Saint-Germain FC (FRA)  1-4 pen. 0-1 a.e.t. (0-1, 0-1)
"""


def test_parse_openfootball_ucl_stages_and_rounds():
    matches = parse_openfootball_ucl(SAMPLE, "ucl")
    assert len(matches) == 4

    league = [m for m in matches if m["stage"] == "league"]
    assert len(league) == 2
    assert all(m["round"] == 1 for m in league)  # league round == matchday

    r16 = next(m for m in matches if m["stage"] == "r16")
    assert r16["round"] == 30  # _UCL_STAGE_ROUND base offset for r16
    assert (r16["home"], r16["away"]) == ("BAR", "RMA")

    final = next(m for m in matches if m["stage"] == "final")
    assert final["round"] == 60
    assert (final["home"], final["away"]) == ("LIV", "PSG")
    # penalty shootout is carried through so the bracket can resolve the tie
    assert (final["homePens"], final["awayPens"]) == (1, 4)


# --------------------------------------------------------------------------- #
# Knockout bracket championship model
# --------------------------------------------------------------------------- #
def _ko(stage, home, away, hg, ag, homePens=None, awayPens=None, date="2025-01-01"):
    return {
        "stage": stage, "round": 30, "date": date,
        "home": home, "away": away, "homeGoals": hg, "awayGoals": ag,
        "homePens": homePens, "awayPens": awayPens,
    }


def test_build_tree_resolves_a_decided_final():
    # Two semi-finals feeding one final; every tie decided on the pitch.
    ko = [
        _ko("sf", "PSG", "RMA", 2, 0),
        _ko("sf", "BAR", "LIV", 1, 0),
        _ko("final", "PSG", "BAR", 1, 0, date="2025-06-01"),
    ]
    final_tie, all_ties, stages = build_tree(ko)
    assert final_tie is not None
    assert final_tie.winner == "PSG"
    assert stages == ["sf", "final"]
    assert len(all_ties) == 3


def test_championship_odds_normalise_and_pick_the_real_champion():
    codes = ["PSG", "RMA", "BAR", "LIV"]
    elo = {"PSG": 1900.0, "RMA": 1880.0, "BAR": 1850.0, "LIV": 1860.0}
    ko = [
        _ko("sf", "PSG", "RMA", 2, 0),
        _ko("sf", "BAR", "LIV", 1, 0),
        _ko("final", "PSG", "BAR", 1, 0, date="2025-06-01"),
    ]
    res = championship(codes, elo, ko)

    # The realised champion is the team that actually won the final.
    assert res["champion"] == "PSG"
    # Pre-knockout odds are a probability distribution over the field (~1).
    total = sum(res["odds"].values())
    assert abs(total - 1.0) < 0.02
    for v in res["odds"].values():
        assert 0.0 <= v <= 1.0

    # Timeline converges: at the last checkpoint the champion sits at ~100%.
    tl = res["timeline"]
    assert tl["checkpoints"][0] == 0
    assert len(tl["labels"]) == len(tl["checkpoints"])
    assert tl["series"]["PSG"][-1] == pytest.approx(100.0, abs=1.0)


def test_championship_currentodds_collapse_to_the_realised_champion():
    # A fully-decided bracket: `currentOdds` fixes every played tie to its real
    # winner, so the live "trophy chance" must read champion 100% / others 0%.
    # This is the field the completed-season summary shows (regression guard for
    # the "champion displayed as a pre-knockout %" bug).
    codes = ["PSG", "RMA", "BAR", "LIV"]
    elo = {"PSG": 1900.0, "RMA": 1880.0, "BAR": 1850.0, "LIV": 1860.0}
    ko = [
        _ko("sf", "PSG", "RMA", 2, 0),
        _ko("sf", "BAR", "LIV", 1, 0),
        _ko("final", "PSG", "BAR", 1, 0, date="2025-06-01"),
    ]
    res = championship(codes, elo, ko)

    assert "currentOdds" in res
    assert res["currentOdds"]["PSG"] == pytest.approx(1.0, abs=1e-6)
    assert sum(v for c, v in res["currentOdds"].items() if c != "PSG") == pytest.approx(0.0, abs=1e-6)
    # The pre-knockout `odds` are still a spread over the field (not collapsed).
    assert res["odds"]["PSG"] < 1.0


def test_championship_currentodds_on_undecided_final_is_a_distribution():
    # If the final isn't played yet, currentOdds must remain a probability spread
    # over the still-alive finalists (no premature 100%).
    codes = ["PSG", "RMA", "BAR", "LIV"]
    elo = {"PSG": 1900.0, "RMA": 1880.0, "BAR": 1850.0, "LIV": 1860.0}
    ko = [
        _ko("sf", "PSG", "RMA", 2, 0),
        _ko("sf", "BAR", "LIV", 1, 0),
        _ko("final", "PSG", "BAR", None, None, date="2025-06-01"),  # not played
    ]
    res = championship(codes, elo, ko)
    # only the two finalists can still win; each strictly between 0 and 1
    assert 0.0 < res["currentOdds"]["PSG"] < 1.0
    assert 0.0 < res["currentOdds"]["BAR"] < 1.0
    assert res["currentOdds"]["RMA"] == pytest.approx(0.0, abs=1e-6)
    assert res["currentOdds"]["LIV"] == pytest.approx(0.0, abs=1e-6)
    assert sum(res["currentOdds"].values()) == pytest.approx(1.0, abs=0.02)


# --------------------------------------------------------------------------- #
# Preseason (no-fixtures) Elo forecast
# --------------------------------------------------------------------------- #
def test_preseason_odds_normalise_and_favour_strength():
    # Before the draw is published there is no bracket, so the forecast is a
    # strength-only Monte Carlo. Odds must be a proper distribution over the
    # field and rank the strongest club ahead of the weakest.
    codes = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
    elo = {
        "AAA": 2000.0, "BBB": 1900.0, "CCC": 1800.0,
        "DDD": 1700.0, "EEE": 1600.0, "FFF": 1500.0,
    }
    odds = preseason_odds(codes, elo, n_sims=4000)

    assert set(odds) == set(codes)
    assert abs(sum(odds.values()) - 1.0) < 0.02
    for v in odds.values():
        assert 0.0 <= v <= 1.0
    # The clear Elo favourite must out-rank the clear underdog.
    assert odds["AAA"] > odds["FFF"]
    # A 500-Elo gap can't leave the underdog as the projected winner.
    assert odds["AAA"] == max(odds.values())


def test_preseason_odds_edge_cases():
    # A tilde-prefixed placeholder code (bye/qualifier slot) is excluded, and the
    # trivial one/zero-club fields degenerate gracefully.
    assert preseason_odds([], {}) == {}
    assert preseason_odds(["ONE"], {"ONE": 1500.0}) == {"ONE": 1.0}
    odds = preseason_odds(["AAA", "~TBD"], {"AAA": 1800.0}, n_sims=200)
    assert odds == {"AAA": 1.0}
