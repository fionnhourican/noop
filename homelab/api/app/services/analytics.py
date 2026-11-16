"""Ported NOOP physiological analytics (HRV, Recovery, Strain).

Faithfully ports logic from:
- Packages/StrandAnalytics/Sources/StrandAnalytics/RecoveryScorer.swift
- Packages/StrandAnalytics/Sources/StrandAnalytics/StrainScorer.swift
- Tools/linux-capture/decode_features.py
"""

import math
from typing import List, Optional, Tuple


def calculate_rr_stats(intervals_ms: List[int]) -> Tuple[int, Optional[float], Optional[float]]:
    """Calculate (count, mean_ms, rmssd) for a series of R-R intervals in ms.

    Non-positive intervals (< 0 or 0 placeholders) are discarded.
    RMSSD requires at least 2 valid successive intervals.
    """
    valid = [x for x in intervals_ms if isinstance(x, (int, float)) and x > 0]
    if not valid:
        return 0, None, None

    n = len(valid)
    mean_ms = sum(valid) / n
    if n < 2:
        return n, round(mean_ms, 2), None

    diffs = [valid[i + 1] - valid[i] for i in range(n - 1)]
    variance = sum(d * d for d in diffs) / len(diffs)
    rmssd = math.sqrt(variance)

    return n, round(mean_ms, 2), round(rmssd, 2)


def calculate_recovery_score(
    hrv_rmssd: float,
    resting_hr: float,
    hrv_baseline_mean: float = 65.0,
    hrv_baseline_std: float = 15.0,
    rhr_baseline_mean: float = 58.0,
    rhr_baseline_std: float = 4.0,
    sleep_performance_pct: Optional[float] = None,  # 0.0 - 100.0
    respiratory_rate: Optional[float] = None,
    resp_baseline_mean: float = 14.5,
    resp_baseline_std: float = 1.0,
    skin_temp_deviation_c: Optional[float] = None,  # delta from 0 deg C
) -> Tuple[float, str]:
    """Calculate a 0.0–100.0 Recovery score ported from NOOP's RecoveryScorer.swift.

    Uses a baseline-normalized z-score composite squashed via logistic function.
    Anchored so z = 0 -> ~58% (population average recovery).
    Missing optional terms are dropped and weights renormalize.
    """
    terms = []
    weights = []

    # 1. HRV term (dominant, weight 0.55)
    std_hrv = max(hrv_baseline_std, 1.0)
    z_hrv = (hrv_rmssd - hrv_baseline_mean) / std_hrv
    terms.append(z_hrv)
    weights.append(0.55)

    # 2. Resting HR term (weight 0.20, lower RHR -> higher recovery)
    std_rhr = max(rhr_baseline_std, 0.5)
    z_rhr = (rhr_baseline_mean - resting_hr) / std_rhr
    terms.append(z_rhr)
    weights.append(0.20)

    # 3. Sleep quality / performance (weight 0.15)
    if sleep_performance_pct is not None:
        # Standardized around 85% ideal sleep performance
        z_sleep = (sleep_performance_pct - 85.0) / 10.0
        terms.append(z_sleep)
        weights.append(0.15)

    # 4. Respiratory rate (weight 0.05, lower resp -> higher recovery)
    if respiratory_rate is not None:
        std_resp = max(resp_baseline_std, 0.2)
        z_resp = (resp_baseline_mean - respiratory_rate) / std_resp
        terms.append(z_resp)
        weights.append(0.05)

    # 5. Skin temperature deviation penalty (weight 0.05, symmetric penalty)
    if skin_temp_deviation_c is not None:
        # Penalty for deviation away from baseline 0.0 (+/- 0.5 deg C scale)
        z_temp = -abs(skin_temp_deviation_c) / 0.5
        terms.append(z_temp)
        weights.append(0.05)

    # Renormalize active weights
    total_w = sum(weights)
    composite_z = sum(t * (w / total_w) for t, w in zip(terms, weights))

    # Logistic squashing: 1 / (1 + exp(-k * (z - z0)))
    # At z = 0: 1 / (1 + exp(-(-0.32))) = 1 / (1 + 1.377) = ~42%?
    # NOOP formula: squashed so z=0 -> ~58%:
    # 100 / (1 + exp(- (0.7 * z + 0.323)))
    # When z = 0: 1 / (1 + exp(-0.323)) = 1 / (1 + 0.724) = 0.58 (58%)
    recovery = 100.0 / (1.0 + math.exp(-(0.7 * composite_z + 0.323)))
    bounded = max(1.0, min(99.0, recovery))

    return round(bounded, 1), "noop_recovery_v1"


def calculate_banister_trimp(
    hr_bpm: int,
    rest_hr: int = 50,
    max_hr: int = 190,
    is_female: bool = False,
) -> float:
    """Calculate Banister TRIMP accumulation for a 1-second heart rate sample.

    Morton, Fitz-Clarke and Banister (1990):
      Men: 0.64 * y * exp(1.92 * y)
      Women: 0.86 * y * exp(1.67 * y)
    where y = (HR - HR_rest) / (HR_max - HR_rest).
    """
    if hr_bpm <= rest_hr:
        return 0.0

    hr_reserve = max_hr - rest_hr
    if hr_reserve <= 0:
        return 0.0

    y = max(0.0, min(1.0, (hr_bpm - rest_hr) / hr_reserve))

    if is_female:
        return 0.86 * y * math.exp(1.67 * y)
    else:
        return 0.64 * y * math.exp(1.92 * y)


def trimp_to_strain(accumulated_trimp: float, day_trimp_ceiling: float = 300.0) -> float:
    """Map accumulated TRIMP to a 0.0 - 21.0 WHOOP-scale day strain score.

    Uses an asymptotic logarithmic curve: strain = 21 * (1 - exp(-trimp / ceiling)).
    """
    if accumulated_trimp <= 0:
        return 0.0
    strain = 21.0 * (1.0 - math.exp(-accumulated_trimp / max(day_trimp_ceiling, 1.0)))
    return round(max(0.0, min(21.0, strain)), 2)
