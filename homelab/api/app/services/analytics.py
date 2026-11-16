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


# =========================================================================
# Phase 1: Health Monitor, Vitals Baseline & Illness Early Warning
# Faithfully ports logic from:
# - Packages/StrandAnalytics/Sources/StrandAnalytics/VitalBands.swift
# - Packages/StrandAnalytics/Sources/StrandAnalytics/IllnessSignalEngine.swift
# - Packages/StrandAnalytics/Sources/StrandAnalytics/SleepDebt.swift
# =========================================================================


POPULATION_VITAL_RANGES = {
    "resting_heart_rate": (40.0, 100.0),      # bpm
    "hrv_rmssd": (20.0, 150.0),                # ms
    "respiratory_rate": (12.0, 20.0),          # breaths/min
    "skin_temp_deviation": (-1.0, 1.0),        # deg C
    "spo2_pct": (95.0, 100.0),                 # %
}

VITAL_UNITS = {
    "resting_heart_rate": "bpm",
    "hrv_rmssd": "ms",
    "respiratory_rate": "rpm",
    "skin_temp_deviation": "°C",
    "spo2_pct": "%",
}

VITAL_LABELS = {
    "resting_heart_rate": "Resting Heart Rate",
    "hrv_rmssd": "Heart Rate Variability",
    "respiratory_rate": "Respiratory Rate",
    "skin_temp_deviation": "Skin Temp Deviation",
    "spo2_pct": "Blood Oxygen",
}


def calculate_vital_bands(
    metric_key: str,
    value: Optional[float],
    history: List[Optional[float]],
    sigma_k: float = 2.0,
    min_nights_trust: int = 14,
) -> dict:
    """Calculate personal baseline banding for a vital metric ported from VitalBands.swift.

    In-range is judged against the user's OWN trailing baseline (mean +/- sigma_k * std)
    once at least min_nights_trust valid nights exist.
    Until then, population ranges are used as fallback.
    """
    label = VITAL_LABELS.get(metric_key, metric_key.replace("_", " ").title())
    unit = VITAL_UNITS.get(metric_key, "")
    pop_min, pop_max = POPULATION_VITAL_RANGES.get(metric_key, (0.0, 100.0))

    if value is None:
        return {
            "metric": metric_key,
            "label": label,
            "value": None,
            "unit": unit,
            "band": "no_data",
            "basis": "population",
            "baseline_mean": None,
            "baseline_min": round(pop_min, 1),
            "baseline_max": round(pop_max, 1),
            "nights_count": 0,
            "z_score": None,
        }

    # Filter usable history
    valid_history = [float(v) for v in history if v is not None and not math.isnan(v)]
    n_nights = len(valid_history)

    # SpO2 is always evaluated against population floor (clinical safety)
    if metric_key == "spo2_pct":
        in_range = pop_min <= value <= pop_max
        return {
            "metric": metric_key,
            "label": label,
            "value": round(value, 1),
            "unit": unit,
            "band": "in_range" if in_range else "out_of_range",
            "basis": "population",
            "baseline_mean": 98.0,
            "baseline_min": round(pop_min, 1),
            "baseline_max": round(pop_max, 1),
            "nights_count": n_nights,
            "z_score": None,
        }

    if n_nights >= min_nights_trust:
        mean_val = sum(valid_history) / n_nights
        variance = sum((x - mean_val) ** 2 for x in valid_history) / max(1, n_nights - 1)
        stdev = math.sqrt(variance)
        # Avoid zero division with noise floor
        stdev_safe = max(stdev, 0.2 if metric_key == "skin_temp_deviation" else 0.5)

        z = (value - mean_val) / stdev_safe
        in_range = abs(z) <= sigma_k
        baseline_min = mean_val - 1.5 * stdev_safe
        baseline_max = mean_val + 1.5 * stdev_safe

        return {
            "metric": metric_key,
            "label": label,
            "value": round(value, 2 if metric_key == "skin_temp_deviation" else 1),
            "unit": unit,
            "band": "in_range" if in_range else "out_of_range",
            "basis": "personal",
            "baseline_mean": round(mean_val, 1),
            "baseline_min": round(baseline_min, 1),
            "baseline_max": round(baseline_max, 1),
            "nights_count": n_nights,
            "z_score": round(z, 2),
        }
    else:
        # Population fallback
        in_range = pop_min <= value <= pop_max
        mean_val = (pop_min + pop_max) / 2.0
        return {
            "metric": metric_key,
            "label": label,
            "value": round(value, 2 if metric_key == "skin_temp_deviation" else 1),
            "unit": unit,
            "band": "in_range" if in_range else "out_of_range",
            "basis": "population",
            "baseline_mean": round(mean_val, 1),
            "baseline_min": round(pop_min, 1),
            "baseline_max": round(pop_max, 1),
            "nights_count": n_nights,
            "z_score": None,
        }


def evaluate_illness(
    rhr_z: Optional[float] = None,
    skin_temp_z: Optional[float] = None,
    hrv_z: Optional[float] = None,
    resp_z: Optional[float] = None,
    confounders: Optional[List[str]] = None,
    baseline_trusted: bool = True,
    already_unwell: bool = False,
) -> dict:
    """Evaluate illness anomaly score ported from NOOP's IllnessSignalEngine.swift.

    Orientations:
    - RHR up -> positive illness-ward
    - Skin Temp up -> positive illness-ward
    - Respiration up -> positive illness-ward
    - HRV drop -> negative HRV z converted to positive illness-ward

    Thresholds:
    - signalZThreshold = 2.0
    - kZToScore = 22.0
    - perSignalCap = 40.0
    - raiseThreshold = 50.0
    - mildThreshold = 25.0
    - minCorroboratingSignals = 2
    """
    signal_z_threshold = 2.0
    k_z_to_score = 22.0
    per_signal_cap = 40.0
    raise_threshold = 50.0
    mild_threshold = 25.0
    min_corroborating = 2
    confounder_dampen = 0.45
    disclaimer = "On-device estimate — not a diagnosis."

    # Convert signals to illness-ward deviations
    # HRV drop is illness-ward: invert sign so HRV drop (z < 0) becomes positive
    hrv_illnessward = -hrv_z if hrv_z is not None else None

    signals = [
        ("resting_heart_rate", rhr_z, "Resting HR elevated"),
        ("skin_temp", skin_temp_z, "Skin temp elevated"),
        ("hrv", hrv_illnessward, "HRV depressed"),
        ("respiration", resp_z, "Respiratory rate elevated"),
    ]

    raw_score = 0.0
    fired_signals = []
    for key, z_val, label in signals:
        if z_val is None:
            continue
        over = z_val - signal_z_threshold
        if over > 0:
            fired_signals.append(label)
            raw_score += min(per_signal_cap, k_z_to_score * over)

    score = min(100.0, raw_score)
    signal_count = len(fired_signals)

    if not baseline_trusted:
        return {
            "score": round(score, 1),
            "level": "quiet",
            "fired_signals": fired_signals,
            "suppressed_by": [],
            "signal_count": signal_count,
            "message": "Still learning your personal baseline — keeping an eye out.",
            "copy": f"Baseline building ({disclaimer})",
            "disclaimer": disclaimer,
        }

    if already_unwell:
        agreeing = score >= mild_threshold and signal_count >= 1
        copy_text = (
            f"Rest up — you logged feeling unwell, and your numbers agree. {disclaimer}"
            if agreeing
            else f"Rest up — you logged feeling unwell. Take it easy today. {disclaimer}"
        )
        return {
            "score": round(score, 1),
            "level": "already_unwell",
            "fired_signals": fired_signals,
            "suppressed_by": [],
            "signal_count": signal_count,
            "message": "Rest up and take it easy.",
            "copy": copy_text,
            "disclaimer": disclaimer,
        }

    active_confounders = confounders or []
    if score >= mild_threshold and signal_count >= min_corroborating and active_confounders:
        damped_score = score * confounder_dampen
        confounder_str = ", ".join(active_confounders)
        copy_text = f"Signals shifted, but recent {confounder_str} explains it. Take care. {disclaimer}"
        return {
            "score": round(damped_score, 1),
            "level": "suppressed",
            "fired_signals": fired_signals,
            "suppressed_by": active_confounders,
            "signal_count": signal_count,
            "message": f"Explained by {confounder_str}.",
            "copy": copy_text,
            "disclaimer": disclaimer,
        }

    if score >= raise_threshold and signal_count >= min_corroborating:
        sig_str = ", ".join(fired_signals)
        copy_text = f"Your body looks strained ({sig_str}). Consider taking it easy. {disclaimer}"
        return {
            "score": round(score, 1),
            "level": "raised",
            "fired_signals": fired_signals,
            "suppressed_by": [],
            "signal_count": signal_count,
            "message": "Multi-signal anomaly detected.",
            "copy": copy_text,
            "disclaimer": disclaimer,
        }

    if score >= mild_threshold:
        return {
            "score": round(score, 1),
            "level": "mild",
            "fired_signals": fired_signals,
            "suppressed_by": [],
            "signal_count": signal_count,
            "message": "Mild biometric deviation noted.",
            "copy": f"Minor shift in vitals noted. {disclaimer}",
            "disclaimer": disclaimer,
        }

    return {
        "score": round(score, 1),
        "level": "quiet",
        "fired_signals": fired_signals,
        "suppressed_by": [],
        "signal_count": signal_count,
        "message": "All vitals in typical ranges.",
        "copy": f"Vitals normal. {disclaimer}",
        "disclaimer": disclaimer,
    }


def calculate_sleep_debt_ledger(
    nightly_slept_min_series: List[float],
    need_hours: float = 8.0,
    window_nights: int = 14,
) -> dict:
    """Calculate running sleep debt ledger ported from SleepDebt.swift.

    - 55% of any unmet need carries forward: next_debt = 0.55 * max(0, need + debt - slept)
    - Calculated debts < 10.0 minutes clear to 0.0 (too small to be actionable).
    """
    need_min = max(need_hours, 0.0) * 60.0
    cap = max(window_nights, 1)

    # Filter positive slept minutes and take latest cap
    usable = [m for m in nightly_slept_min_series if m > 0][-cap:]

    debt = 0.0
    for slept in usable:
        calculated_debt = 0.55 * max(0.0, need_min + debt - slept)
        if calculated_debt < 10.0:
            debt = 0.0
        else:
            debt = calculated_debt

    return {
        "balance_min": round(debt, 1),
        "need_min": round(need_min, 1),
        "window_nights": len(usable),
        "is_debt": debt > 0,
    }
