"""
Unit tests for stage-6 Monte-Carlo season simulation (``club_simulate``).

Covers the deterministic standings accumulator (points / GD / played), the
expected-goals mapping, and the top-level ``simulate`` contract: every bracket
probability is a valid distribution and the "eliminated ⇒ 0 %" guarantee holds.
Runs with a small ``n_sims`` so it stays fast and deterministic (fixed SEED).
"""
import pytest

from club_simulate import (
    _base_standings,
    _expected_goals,
    simulate,
    title_race_timeline,
)


def _played(home, away, hg, ag):
    return {"home": home, "away": away, "homeGoals": hg, "awayGoals": ag}


def _fixture(home, away):
    return {"home": home, "away": away, "homeGoals": None, "awayGoals": None}


# --------------------------------------------------------------------------- #
# standings accumulator
# --------------------------------------------------------------------------- #
def test_base_standings_points_and_goal_difference():
    codes = ["ARS", "CHE", "LIV"]
    completed = [
        _played("ARS", "CHE", 2, 0),   # ARS win
        _played("CHE", "LIV", 1, 1),   # draw
        _played("LIV", "ARS", 0, 3),   # ARS win
    ]
    base = _base_standings(codes, completed)
    assert base["ARS"]["pts"] == 6
    assert base["ARS"]["gf"] - base["ARS"]["ga"] == 5   # (2-0)+(3-0)
    assert base["ARS"]["played"] == 2
    assert base["CHE"]["pts"] == 1
    assert base["LIV"]["pts"] == 1


def test_base_standings_ignores_unknown_clubs():
    base = _base_standings(["ARS"], [_played("ARS", "ZZZ", 1, 0)])
    # The ARS/ZZZ game references a club not in the code list → skipped entirely.
    assert base["ARS"]["played"] == 0


def test_expected_goals_favour_the_stronger_side():
    lh, la = _expected_goals(1800, 1500)
    assert lh > la
    assert lh > 0.0 and la > 0.0


# --------------------------------------------------------------------------- #
# full simulation contract
# --------------------------------------------------------------------------- #
def _round_robin(codes):
    """Every ordered pair once (home & away) — a mini double round-robin."""
    fixtures = []
    for h in codes:
        for a in codes:
            if h != a:
                fixtures.append(_fixture(h, a))
    return fixtures


def test_simulate_returns_valid_probability_distributions():
    codes = ["ARS", "CHE", "LIV", "MCI"]
    elo = {"ARS": 1700, "CHE": 1600, "LIV": 1650, "MCI": 1550}
    remaining = _round_robin(codes)
    out = simulate(codes, elo, completed=[], remaining=remaining,
                   ucl=2, europa=1, releg=1, n_sims=300)

    title_total = 0.0
    for c in codes:
        row = out[c]
        for key in ("title", "ucl", "europa", "relegation"):
            assert 0.0 <= row[key] <= 1.0
        assert len(row["positionDist"]) == len(codes)
        assert sum(row["positionDist"]) == pytest.approx(1.0, abs=2e-3)
        title_total += row["title"]
    # Exactly one champion across the league (rounded probs, so small tolerance).
    assert title_total == pytest.approx(1.0, abs=2e-3)


def test_simulate_zeroes_a_mathematically_eliminated_club():
    """A club that cannot catch the leader on maximum points has 0 % title."""
    codes = ["ARS", "CHE", "LIV", "MCI"]
    elo = {c: 1500 for c in codes}
    # ARS already has a huge lead; only one fixture remains for everyone.
    completed = [
        _played("ARS", "CHE", 5, 0),
        _played("ARS", "LIV", 5, 0),
        _played("ARS", "MCI", 5, 0),
        _played("CHE", "LIV", 0, 0),
        _played("CHE", "MCI", 0, 0),
    ]
    remaining = [_fixture("LIV", "MCI")]  # ARS is idle and uncatchable
    out = simulate(codes, elo, completed=completed, remaining=remaining,
                   ucl=2, europa=1, releg=1, n_sims=300)
    assert out["ARS"]["title"] == pytest.approx(1.0, abs=1e-6)
    # CHE has 2 pts + 0 remaining games → cannot reach ARS's 9 → 0 % title.
    assert out["CHE"]["title"] == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# title-race timeline
# --------------------------------------------------------------------------- #
CODES4 = ["ARS", "CHE", "LIV", "MCI"]

# A 4-club double round-robin (6 matchdays, 2 games each) laid out so every club
# plays exactly once per round. ARS wins all six of its games; the games between
# the other three are draws — so ARS is the runaway, uncatchable champion.
_SCHEDULE = [
    (1, "ARS", "CHE", 2, 0), (1, "LIV", "MCI", 1, 1),
    (2, "ARS", "LIV", 2, 0), (2, "MCI", "CHE", 1, 1),
    (3, "ARS", "MCI", 2, 0), (3, "CHE", "LIV", 1, 1),
    (4, "CHE", "ARS", 0, 2), (4, "MCI", "LIV", 1, 1),
    (5, "LIV", "ARS", 0, 2), (5, "CHE", "MCI", 1, 1),
    (6, "MCI", "ARS", 0, 2), (6, "LIV", "CHE", 1, 1),
]


def _ordered(*, completed_through: int) -> list[dict]:
    """Build an ``ordered`` match list; rounds <= ``completed_through`` are played."""
    out = []
    for rnd, home, away, hg, ag in _SCHEDULE:
        done = rnd <= completed_through
        out.append({
            "home": home, "away": away, "round": rnd,
            "status": "completed" if done else "upcoming",
            "homeGoals": hg if done else None,
            "awayGoals": ag if done else None,
        })
    return out


def test_timeline_is_empty_before_any_results():
    race = title_race_timeline(CODES4, _ordered(completed_through=0), n_sims=200)
    assert race["checkpoints"] == []
    assert race["playedAt"] == []
    assert all(series == [] for series in race["series"].values())


def test_timeline_probabilities_form_a_distribution_at_every_checkpoint():
    race = title_race_timeline(CODES4, _ordered(completed_through=6), n_sims=400)
    # Checkpoints run 0..lastCompletedRound and the played count is non-decreasing.
    assert race["checkpoints"] == list(range(0, race["lastCompletedRound"] + 1))
    assert race["playedAt"] == sorted(race["playedAt"])
    for k in range(len(race["checkpoints"])):
        total = sum(race["series"][c][k] for c in CODES4)
        assert total == pytest.approx(1.0, abs=1e-2)   # exactly one champion
        for c in CODES4:
            assert 0.0 <= race["series"][c][k] <= 1.0


def test_timeline_converges_to_the_actual_champion():
    race = title_race_timeline(CODES4, _ordered(completed_through=6), n_sims=400)
    last = len(race["checkpoints"]) - 1
    # Season fully played out → ARS (18 pts) is champion with certainty; the
    # other three, mathematically eliminated, are hard-zeroed.
    assert race["series"]["ARS"][last] == pytest.approx(1.0, abs=1e-9)
    for c in ("CHE", "LIV", "MCI"):
        assert race["series"][c][last] == pytest.approx(0.0, abs=1e-9)


def test_timeline_is_deterministic():
    a = title_race_timeline(CODES4, _ordered(completed_through=4), n_sims=300)
    b = title_race_timeline(CODES4, _ordered(completed_through=4), n_sims=300)
    assert a["series"] == b["series"]
