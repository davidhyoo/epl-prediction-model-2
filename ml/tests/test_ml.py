"""
Unit tests for the deterministic ML core (Elo model, probabilistic metrics,
ensemble blending). Pure-function tests only — no file I/O, no training — so
they run in well under a second with just numpy installed.

Run:
    python -m unittest discover -s ml/tests
    # or
    python ml/tests/test_ml.py
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import common  # noqa: E402
import modeling  # noqa: E402


class TestEloAndGoals(unittest.TestCase):
    def test_elo_equal_ratings_is_even(self):
        self.assertAlmostEqual(common.elo_win_prob(1600, 1600), 0.5, places=9)

    def test_elo_is_monotonic_and_symmetric(self):
        strong = common.elo_win_prob(1800, 1500)
        weak = common.elo_win_prob(1500, 1800)
        self.assertGreater(strong, 0.5)
        self.assertLess(weak, 0.5)
        # Probabilities of the two orientations must sum to 1.
        self.assertAlmostEqual(strong + weak, 1.0, places=9)

    def test_elo_stays_in_open_unit_interval(self):
        for diff in (-1000, -200, 0, 200, 1000):
            p = common.elo_win_prob(1600 + diff, 1600)
            self.assertTrue(0.0 < p < 1.0)

    def test_expected_goals_favour_stronger_team(self):
        lam_a, lam_b = common.expected_goals(1800, 1500)
        self.assertGreater(lam_a, lam_b)
        self.assertGreaterEqual(lam_a, 0.18)
        self.assertGreaterEqual(lam_b, 0.18)


class TestScaling(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(common.clamp(5, 0, 10), 5)
        self.assertEqual(common.clamp(-1, 0, 10), 0)
        self.assertEqual(common.clamp(99, 0, 10), 10)

    def test_scale_0_100_bounds(self):
        self.assertEqual(common.scale_0_100(5, 5, 5), 50.0)  # degenerate range
        self.assertTrue(1.0 <= common.scale_0_100(0, 0, 100) <= 99.0)
        self.assertTrue(1.0 <= common.scale_0_100(100, 0, 100) <= 99.0)


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.y = np.array([0, 1, 2, 0])
        self.perfect = np.array(
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]]
        )

    def test_accuracy_perfect(self):
        self.assertEqual(modeling.accuracy(self.y, self.perfect), 1.0)

    def test_log_loss_perfect_is_tiny(self):
        # Clipped, so not exactly 0, but very small.
        self.assertLess(modeling.log_loss(self.y, self.perfect), 1e-6)

    def test_brier_perfect_is_zero(self):
        self.assertAlmostEqual(modeling.brier(self.y, self.perfect), 0.0, places=9)

    def test_log_loss_penalises_confident_mistakes(self):
        wrong = np.array(
            [[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
        )
        self.assertGreater(
            modeling.log_loss(self.y, wrong), modeling.log_loss(self.y, self.perfect)
        )

    def test_evaluate_model_shape(self):
        out = modeling.evaluate_model(self.y, self.perfect)
        for key in ("accuracy", "logLoss", "brier", "avgConfidence", "ece", "calibration"):
            self.assertIn(key, out)
        self.assertEqual(out["gamesEvaluated"], 4)


class TestEnsemble(unittest.TestCase):
    def test_rows_sum_to_one(self):
        a = np.array([[0.6, 0.3, 0.1], [0.2, 0.3, 0.5]])
        b = np.array([[0.4, 0.4, 0.2], [0.1, 0.2, 0.7]])
        P = modeling.ensemble_proba([a, b], np.array([0.5, 0.5]))
        np.testing.assert_allclose(P.sum(axis=1), np.ones(2), atol=1e-9)

    def test_weighting_shifts_toward_heavier_model(self):
        a = np.array([[0.9, 0.05, 0.05]])
        b = np.array([[0.1, 0.45, 0.45]])
        heavy_a = modeling.ensemble_proba([a, b], np.array([0.9, 0.1]))
        heavy_b = modeling.ensemble_proba([a, b], np.array([0.1, 0.9]))
        self.assertGreater(heavy_a[0, 0], heavy_b[0, 0])

    def test_importance_normalises_and_sorts(self):
        order = common.FEATURE_ORDER
        vals = np.arange(len(order), dtype=float)
        imp = modeling.normalize_importance(vals, order)
        total = sum(item["importance"] for item in imp)
        self.assertAlmostEqual(total, 1.0, places=2)
        # Sorted descending by importance.
        weights = [item["importance"] for item in imp]
        self.assertEqual(weights, sorted(weights, reverse=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
