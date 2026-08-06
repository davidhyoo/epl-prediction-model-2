"""
Unit tests for the deterministic modelling core (``club_modeling``).

Pure-function maths only — the analytic Elo baseline, ensemble blending and the
probabilistic metrics (accuracy / log-loss / Brier / calibration). No training,
no I/O. A stub draw-model stands in for the fitted sklearn draw classifier so we
can exercise ``elo_baseline_proba`` in isolation.
"""
import numpy as np
import pytest

import club_modeling as M
from club_features import FEATURE_ORDER, N_FEATURES

HOME_IDX = FEATURE_ORDER.index("home_adv")
ELO_IDX = FEATURE_ORDER.index("elo_diff")


class _ConstantDrawModel:
    """Stub with the sklearn ``predict_proba`` shape: column 1 = draw prob."""

    def __init__(self, draw: float = 0.25):
        self.draw = draw

    def predict_proba(self, x):
        x = np.asarray(x, dtype=float).reshape(-1, 1)
        p = np.full(len(x), self.draw)
        return np.column_stack([1.0 - p, p])


def _row(elo_diff_points=0.0, home_adv=1.0):
    """Build a single feature row with a given Elo gap (in points)."""
    v = np.zeros(N_FEATURES)
    v[ELO_IDX] = elo_diff_points / 100.0  # stored ÷100
    v[HOME_IDX] = home_adv
    return v.reshape(1, -1)


# --------------------------------------------------------------------------- #
# Elo baseline
# --------------------------------------------------------------------------- #
def test_elo_baseline_rows_sum_to_one():
    X = np.vstack([_row(-300), _row(0), _row(300)])
    P = M.elo_baseline_proba(X, _ConstantDrawModel(0.25))
    np.testing.assert_allclose(P.sum(axis=1), np.ones(3), atol=1e-9)
    assert np.all(P >= 0.0)


def test_elo_baseline_is_monotonic_in_rating_gap():
    dm = _ConstantDrawModel(0.20)
    p_strong = M.elo_baseline_proba(_row(400), dm)[0, 0]
    p_even = M.elo_baseline_proba(_row(0), dm)[0, 0]
    p_weak = M.elo_baseline_proba(_row(-400), dm)[0, 0]
    assert p_strong > p_even > p_weak


def test_elo_baseline_home_advantage_breaks_the_tie():
    """With equal Elo, the home-advantage term must favour the home side."""
    dm = _ConstantDrawModel(0.24)
    P = M.elo_baseline_proba(_row(0, home_adv=1.0), dm)
    assert P[0, 0] > P[0, 2]  # home win prob > away win prob


def test_elo_baseline_respects_draw_model():
    P = M.elo_baseline_proba(_row(0), _ConstantDrawModel(0.30))
    assert P[0, 1] == pytest.approx(0.30, abs=1e-9)


# --------------------------------------------------------------------------- #
# Ensemble blending
# --------------------------------------------------------------------------- #
def test_ensemble_rows_sum_to_one():
    a = np.array([[0.6, 0.3, 0.1], [0.2, 0.3, 0.5]])
    b = np.array([[0.4, 0.4, 0.2], [0.1, 0.2, 0.7]])
    P = M.ensemble_proba([a, b], np.array([0.5, 0.5]))
    np.testing.assert_allclose(P.sum(axis=1), np.ones(2), atol=1e-9)


def test_ensemble_weights_are_normalised_internally():
    a = np.array([[0.9, 0.05, 0.05]])
    b = np.array([[0.1, 0.45, 0.45]])
    # Un-normalised weights (sum 3) must give the same result as normalised ones.
    P1 = M.ensemble_proba([a, b], np.array([2.0, 1.0]))
    P2 = M.ensemble_proba([a, b], np.array([2.0, 1.0]) / 3.0)
    np.testing.assert_allclose(P1, P2, atol=1e-12)


def test_ensemble_shifts_toward_heavier_model():
    a = np.array([[0.9, 0.05, 0.05]])
    b = np.array([[0.1, 0.45, 0.45]])
    heavy_a = M.ensemble_proba([a, b], np.array([0.9, 0.1]))
    heavy_b = M.ensemble_proba([a, b], np.array([0.1, 0.9]))
    assert heavy_a[0, 0] > heavy_b[0, 0]


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
@pytest.fixture
def perfect():
    y = np.array([0, 1, 2, 0])
    P = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                  [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    return y, P


def test_accuracy_perfect(perfect):
    y, P = perfect
    assert M.accuracy(y, P) == 1.0


def test_log_loss_perfect_is_tiny(perfect):
    y, P = perfect
    assert M.log_loss(y, P) < 1e-6  # clipped, so small but not exactly 0


def test_brier_perfect_is_zero(perfect):
    y, P = perfect
    assert M.brier(y, P) == pytest.approx(0.0, abs=1e-9)


def test_log_loss_penalises_confident_mistakes(perfect):
    y, good = perfect
    wrong = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0],
                      [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    assert M.log_loss(y, wrong) > M.log_loss(y, good)


def test_evaluate_model_reports_all_fields(perfect):
    y, P = perfect
    out = M.evaluate_model(y, P)
    for key in ("accuracy", "logLoss", "brier", "avgConfidence",
                "ece", "calibration", "gamesEvaluated"):
        assert key in out
    assert out["gamesEvaluated"] == 4


def test_calibration_bins_stay_in_unit_interval(perfect):
    y, P = perfect
    bins, ece = M.calibration(y, P)
    assert 0.0 <= ece <= 1.0
    for b in bins:
        assert 0.0 <= b["predicted"] <= 1.0
        assert 0.0 <= b["observed"] <= 1.0
        assert b["count"] >= 1


# --------------------------------------------------------------------------- #
# Ensemble weighting from log-loss + importance
# --------------------------------------------------------------------------- #
def test_inverse_logloss_weights_favour_lower_loss_and_sum_to_one():
    w = M.inverse_logloss_weights({"good": 0.5, "bad": 2.0})
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-9)
    assert w["good"] > w["bad"]


def test_normalize_importance_sorts_and_sums_to_one():
    vals = np.arange(len(FEATURE_ORDER), dtype=float)
    imp = M.normalize_importance(vals, FEATURE_ORDER)
    total = sum(item["importance"] for item in imp)
    assert total == pytest.approx(1.0, abs=1e-2)
    weights = [item["importance"] for item in imp]
    assert weights == sorted(weights, reverse=True)
    # Every entry carries a human-readable label.
    assert all(item["label"] for item in imp)
