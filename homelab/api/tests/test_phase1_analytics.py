"""Unit tests for Phase 1 analytics (VitalBands, IllnessSignalEngine, SleepDebt)."""

import unittest
from app.services.analytics import (
    calculate_vital_bands,
    evaluate_illness,
    calculate_sleep_debt_ledger,
)


class TestVitalBands(unittest.TestCase):
    def test_population_fallback_when_history_sparse(self):
        # With < 14 nights, falls back to population ranges
        history = [60.0, 62.0, 58.0]
        res = calculate_vital_bands(
            metric_key="resting_heart_rate",
            value=65.0,
            history=history,
            min_nights_trust=14,
        )
        self.assertEqual(res["basis"], "population")
        self.assertEqual(res["band"], "in_range")
        self.assertEqual(res["nights_count"], 3)

    def test_personal_baseline_evaluation(self):
        # 20 nights of RHR around ~60 with std ~2
        history = [60.0 + (i % 3 - 1) * 1.5 for i in range(20)]
        res = calculate_vital_bands(
            metric_key="resting_heart_rate",
            value=61.0,
            history=history,
            sigma_k=2.0,
            min_nights_trust=14,
        )
        self.assertEqual(res["basis"], "personal")
        self.assertEqual(res["band"], "in_range")
        self.assertIsNotNone(res["z_score"])

    def test_out_of_range_detection(self):
        history = [60.0] * 15
        # 75 is far above baseline 60 (z > 2.0)
        res = calculate_vital_bands(
            metric_key="resting_heart_rate",
            value=75.0,
            history=history,
            sigma_k=2.0,
            min_nights_trust=14,
        )
        self.assertEqual(res["band"], "out_of_range")

    def test_spo2_always_population(self):
        history = [98.0] * 20
        res = calculate_vital_bands(
            metric_key="spo2_pct",
            value=94.0,  # Below 95% floor
            history=history,
        )
        self.assertEqual(res["basis"], "population")
        self.assertEqual(res["band"], "out_of_range")


class TestIllnessSignalEngine(unittest.TestCase):
    def test_quiet_when_signals_normal(self):
        res = evaluate_illness(
            rhr_z=0.2,
            skin_temp_z=0.1,
            hrv_z=-0.1,
            resp_z=0.0,
        )
        self.assertEqual(res["level"], "quiet")
        self.assertEqual(res["score"], 0.0)
        self.assertEqual(res["signal_count"], 0)

    def test_raised_when_two_signals_severely_elevated(self):
        # RHR +4.5 SD, HRV -4.5 SD (negated to +4.5 illness-ward)
        # over = 2.5 each -> raw = min(40, 22 * 2.5) = 40 + 40 = 80 -> raised!
        res = evaluate_illness(
            rhr_z=4.5,
            hrv_z=-4.5,
            skin_temp_z=0.5,
            resp_z=0.2,
        )
        self.assertEqual(res["level"], "raised")
        self.assertGreaterEqual(res["score"], 50.0)
        self.assertIn("Resting HR elevated", res["fired_signals"])
        self.assertIn("HRV depressed", res["fired_signals"])

    def test_confounder_suppresses_anomaly(self):
        res = evaluate_illness(
            rhr_z=4.5,
            hrv_z=-4.5,
            confounders=["alcohol", "late_meal"],
        )
        self.assertEqual(res["level"], "suppressed")
        self.assertIn("alcohol", res["suppressed_by"])


class TestSleepDebt(unittest.TestCase):
    def test_no_debt_when_meeting_need(self):
        # Need 8 hours (480 min), sleeping 480 min every night
        series = [480.0] * 14
        res = calculate_sleep_debt_ledger(series, need_hours=8.0)
        self.assertEqual(res["balance_min"], 0.0)
        self.assertFalse(res["is_debt"])

    def test_debt_accumulates_with_55_pct_carryover(self):
        # Night 1: slept 420 min (60 min deficit) -> 60 * 0.55 = 33 min debt
        series = [420.0]
        res = calculate_sleep_debt_ledger(series, need_hours=8.0)
        self.assertEqual(res["balance_min"], 33.0)
        self.assertTrue(res["is_debt"])

    def test_clears_small_debt_below_10_min(self):
        # Sleeping 470 min (10 min deficit) -> 10 * 0.55 = 5.5 min (< 10 min threshold -> 0.0)
        series = [470.0]
        res = calculate_sleep_debt_ledger(series, need_hours=8.0)
        self.assertEqual(res["balance_min"], 0.0)


if __name__ == "__main__":
    unittest.main()
