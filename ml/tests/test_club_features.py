"""
Unit tests for stage-3 feature engineering (``club_features``).

The single most important property here is **no leakage**: a fixture's feature
vector must be a function of matches that kicked off strictly *before* it, never
of its own result. These tests pin that invariant, plus the chronological Elo /
form / head-to-head bookkeeping and the training-matrix builder.
"""
import numpy as np
import pytest

from club_features import (
    FeatureEngine,
    FEATURE_ORDER,
    N_FEATURES,
    build_season_features,
    build_training_matrix,
    outcome_label,
)

ELO_IDX = FEATURE_ORDER.index("elo_diff")
FORM_IDX = FEATURE_ORDER.index("form_diff")
H2H_IDX = FEATURE_ORDER.index("h2h_diff")


def _match(home, away, hg=None, ag=None, date="2025-08-16"):
    return {"home": home, "away": away, "homeGoals": hg, "awayGoals": ag,
            "date": date, "datetime": f"{date}T15:00:00+00:00"}


# --------------------------------------------------------------------------- #
# outcome labelling
# --------------------------------------------------------------------------- #
def test_outcome_label_mapping():
    assert outcome_label(2, 0) == 0   # home win
    assert outcome_label(1, 1) == 1   # draw
    assert outcome_label(0, 3) == 2   # away win


# --------------------------------------------------------------------------- #
# leakage safety
# --------------------------------------------------------------------------- #
def test_first_fixture_features_are_neutral():
    """With no history, home-vs-away differences must all be zero."""
    eng = FeatureEngine()
    v = eng.features(_match("ARS", "CHE"))
    assert v.shape == (N_FEATURES,)
    assert v[ELO_IDX] == pytest.approx(0.0)
    assert v[FORM_IDX] == pytest.approx(0.0)
    assert v[H2H_IDX] == pytest.approx(0.0)


def test_features_do_not_depend_on_the_matchs_own_result():
    """
    Two identically-primed engines must emit the SAME vector for a fixture
    regardless of whether that fixture's score is filled in — proving the score
    never leaks into its own features.
    """
    prior = _match("LIV", "MCI", hg=2, ag=1, date="2025-08-16")

    eng_a = FeatureEngine()
    eng_a.features(prior); eng_a.observe(prior)
    eng_b = FeatureEngine()
    eng_b.features(prior); eng_b.observe(prior)

    target_blank = _match("ARS", "CHE", date="2025-08-23")
    target_scored = _match("ARS", "CHE", hg=4, ag=0, date="2025-08-23")

    v_blank = eng_a.features(target_blank)
    v_scored = eng_b.features(target_scored)
    np.testing.assert_allclose(v_blank, v_scored, atol=1e-12)


def test_observing_a_home_win_moves_elo_the_right_way():
    eng = FeatureEngine()
    m = _match("ARS", "CHE", hg=3, ag=0, date="2025-08-16")
    eng.features(m)
    eng.observe(m)
    assert eng._get_elo("ARS") > eng._get_elo("CHE")
    # Elo is zero-sum on a single game.
    total = eng._get_elo("ARS") + eng._get_elo("CHE")
    assert total == pytest.approx(2 * 1440.0, abs=1e-6)  # PROMOTED_ELO prior


def test_form_and_h2h_reflect_prior_results():
    eng = FeatureEngine()
    # ARS beats CHE twice; ARS should carry better form and a +ve h2h edge.
    for d in ("2025-08-16", "2025-09-20"):
        m = _match("ARS", "CHE", hg=2, ag=0, date=d)
        eng.features(m); eng.observe(m)
    v = eng.features(_match("ARS", "CHE", date="2025-10-25"))
    assert v[FORM_IDX] > 0.0
    assert v[H2H_IDX] > 0.0


# --------------------------------------------------------------------------- #
# training-matrix builder
# --------------------------------------------------------------------------- #
def test_build_training_matrix_shapes_and_labels():
    corpus = [
        _match("ARS", "CHE", 2, 0, "2025-08-16"),
        _match("LIV", "MCI", 1, 1, "2025-08-17"),
        _match("CHE", "LIV", 0, 2, "2025-08-24"),
    ]
    X, y, eng = build_training_matrix(corpus)
    assert X.shape == (3, N_FEATURES)
    assert y.tolist() == [0, 1, 2]
    assert not np.isnan(X).any()
    assert isinstance(eng, FeatureEngine)


def test_build_training_matrix_is_chronological():
    """Rows must be emitted in date order even if the corpus is shuffled."""
    corpus = [
        _match("CHE", "LIV", 0, 2, "2025-08-24"),
        _match("ARS", "CHE", 2, 0, "2025-08-16"),
        _match("LIV", "MCI", 1, 1, "2025-08-17"),
    ]
    _, y, _ = build_training_matrix(corpus)
    # Sorted order is ARS/CHE (home win=0), LIV/MCI (draw=1), CHE/LIV (away=2).
    assert y.tolist() == [0, 1, 2]


def test_unplayed_fixtures_do_not_move_elo():
    """Upcoming (goalless) fixtures never call a scoring update, so — within a
    season (no summer break) — Elo is frozen across ``build_season_features``."""
    eng = FeatureEngine()
    seed = _match("ARS", "CHE", 3, 0, "2025-08-16")
    eng.features(seed); eng.observe(seed)
    before = eng._get_elo("ARS")

    fixtures = [_match("ARS", "LIV", date="2025-08-23"),
                _match("CHE", "ARS", date="2025-08-30")]
    X, ordered = build_season_features(eng, fixtures)
    assert X.shape == (2, N_FEATURES)
    assert eng._get_elo("ARS") == pytest.approx(before, abs=1e-6)
    # Each row is annotated with the pre-match Elo snapshot for the UI.
    assert all("_elo_home" in m and "_elo_away" in m for m in ordered)


def test_summer_break_regresses_elo_toward_the_mean():
    """A gap over the season boundary pulls Elo 25% back toward 1500 exactly
    once, reflecting squad turnover between campaigns."""
    eng = FeatureEngine()
    seed = _match("ARS", "CHE", 5, 0, "2025-08-16")
    eng.features(seed); eng.observe(seed)
    high = eng._get_elo("ARS")

    # A fixture ~a year later crosses the > 60-day season gap.
    eng.features(_match("ARS", "LIV", date="2026-08-15"))
    regressed = eng._get_elo("ARS")
    expected = 0.75 * high + 0.25 * 1500.0
    assert regressed == pytest.approx(expected, abs=1e-6)
    # Regression always shrinks the distance to the 1500 baseline.
    assert abs(regressed - 1500.0) < abs(high - 1500.0)
