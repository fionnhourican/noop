"""Unit tests for ported NOOP physiological analytics."""

import pytest
from app.services.analytics import (
    calculate_banister_trimp,
    calculate_recovery_score,
    calculate_rr_stats,
    trimp_to_strain,
)


class TestRRStats:
    def test_empty_intervals(self):
        count, mean, rmssd = calculate_rr_stats([])
        assert count == 0
        assert mean is None
        assert rmssd is None

    def test_single_interval(self):
        count, mean, rmssd = calculate_rr_stats([800])
        assert count == 1
        assert mean == 800.0
        assert rmssd is None  # RMSSD requires >= 2 successive intervals

    def test_valid_intervals_calculation(self):
        # 800, 850, 820 -> diffs: +50, -30 -> squares: 2500, 900 -> mean: 1700 -> sqrt: ~41.23
        count, mean, rmssd = calculate_rr_stats([800, 850, 820])
        assert count == 3
        assert mean == round((800 + 850 + 820) / 3, 2)
        assert rmssd == 41.23

    def test_filters_non_positive_and_placeholders(self):
        # 0 is strap placeholder for missing beat slot
        count, mean, rmssd = calculate_rr_stats([800, 0, -50, 850, 820])
        assert count == 3
        assert rmssd == 41.23


class TestRecoveryScore:
    def test_baseline_anchor_recovery(self):
        # When user matches baseline exactly on HRV and RHR, recovery should anchor around ~58%
        score, alg = calculate_recovery_score(
            hrv_rmssd=65.0,
            resting_hr=58.0,
            hrv_baseline_mean=65.0,
            rhr_baseline_mean=58.0,
        )
        assert alg == "noop_recovery_v1"
        assert 55.0 <= score <= 60.0

    def test_elevated_hrv_and_lower_rhr_boosts_recovery(self):
        # High HRV + low RHR -> High recovery (>80%)
        score, _ = calculate_recovery_score(
            hrv_rmssd=95.0,  # +2 SD above baseline
            resting_hr=50.0,  # -2 SD below baseline
            hrv_baseline_mean=65.0,
            hrv_baseline_std=15.0,
            rhr_baseline_mean=58.0,
            rhr_baseline_std=4.0,
        )
        assert score >= 80.0

    def test_suppressed_hrv_and_elevated_rhr_lowers_recovery(self):
        # Low HRV + high RHR -> Red recovery (<35%)
        score, _ = calculate_recovery_score(
            hrv_rmssd=35.0,
            resting_hr=66.0,
            hrv_baseline_mean=65.0,
            hrv_baseline_std=15.0,
            rhr_baseline_mean=58.0,
            rhr_baseline_std=4.0,
        )
        assert score <= 35.0

    def test_skin_temperature_penalty(self):
        score_normal, _ = calculate_recovery_score(
            hrv_rmssd=65.0,
            resting_hr=58.0,
            skin_temp_deviation_c=0.0,
        )
        score_fever, _ = calculate_recovery_score(
            hrv_rmssd=65.0,
            resting_hr=58.0,
            skin_temp_deviation_c=1.2,  # +1.2 deg fever
        )
        assert score_fever < score_normal


class TestStrainScorer:
    def test_resting_produces_zero_trimp(self):
        trimp = calculate_banister_trimp(hr_bpm=50, rest_hr=50, max_hr=190)
        assert trimp == 0.0

    def test_elevated_hr_accumulates_trimp(self):
        trimp_mod = calculate_banister_trimp(hr_bpm=120, rest_hr=50, max_hr=190)
        trimp_high = calculate_banister_trimp(hr_bpm=175, rest_hr=50, max_hr=190)
        assert trimp_mod > 0.0
        assert trimp_high > trimp_mod

    def test_strain_mapping_bounds(self):
        assert trimp_to_strain(0.0) == 0.0
        # 100 trimp
        strain_100 = trimp_to_strain(100.0, day_trimp_ceiling=300.0)
        assert 0.0 < strain_100 < 21.0
        # Huge trimp approaches 21.0 asymptotic ceiling
        strain_huge = trimp_to_strain(5000.0, day_trimp_ceiling=300.0)
        assert 20.9 <= strain_huge <= 21.0
