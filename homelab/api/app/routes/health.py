"""Health monitor, vitals baseline banding, and illness early warning routes."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import BiometricRecord, RecoveryMetric
from app.schemas.domain import (
    IllnessEvaluationResponse,
    VitalBandItem,
    VitalSignsResponse,
)
from app.security import get_current_dashboard_user
from app.services.analytics import calculate_vital_bands, evaluate_illness

router = APIRouter(prefix="/health", tags=["Health Monitor"])


async def compute_device_vitals_and_illness(
    db: AsyncSession,
    device_id: Optional[str] = None,
) -> tuple[VitalSignsResponse, IllnessEvaluationResponse]:
    """Helper to query 28-day history and compute vitals & illness status."""
    # 1. Fetch latest recovery and history
    rec_q = select(RecoveryMetric)
    if device_id:
        rec_q = rec_q.where(RecoveryMetric.device_id == device_id)
    rec_history_res = await db.execute(
        rec_q.order_by(RecoveryMetric.date.desc()).limit(28)
    )
    rec_history = list(rec_history_res.scalars().all())

    # 2. Fetch latest biometrics and history for SpO2 / skin temp if needed
    bio_q = select(BiometricRecord)
    if device_id:
        bio_q = bio_q.where(BiometricRecord.device_id == device_id)
    bio_history_res = await db.execute(
        bio_q.order_by(BiometricRecord.timestamp.desc()).limit(100)
    )
    bio_history = list(bio_history_res.scalars().all())

    latest_rec = rec_history[0] if rec_history else None
    latest_bio = bio_history[0] if bio_history else None

    # Series histories (excluding today / latest reading for baseline calculation)
    rhr_hist: List[Optional[float]] = [r.resting_heart_rate for r in rec_history[1:] if r.resting_heart_rate is not None]
    hrv_hist: List[Optional[float]] = [r.hrv_rmssd for r in rec_history[1:] if r.hrv_rmssd is not None]
    resp_hist: List[Optional[float]] = [r.respiratory_rate for r in rec_history[1:] if r.respiratory_rate is not None]
    temp_hist: List[Optional[float]] = [r.skin_temp_deviation for r in rec_history[1:] if r.skin_temp_deviation is not None]
    spo2_hist: List[Optional[float]] = [b.spo2_pct for b in bio_history if b.spo2_pct is not None]

    latest_rhr = latest_rec.resting_heart_rate if latest_rec else None
    latest_hrv = latest_rec.hrv_rmssd if latest_rec else None
    latest_resp = latest_rec.respiratory_rate if latest_rec else (latest_bio.respiratory_rate if latest_bio else None)
    latest_temp = latest_rec.skin_temp_deviation if latest_rec else (latest_bio.skin_temp_c if latest_bio else None)
    latest_spo2 = latest_bio.spo2_pct if latest_bio else 98.0

    # Calculate Vital Bands
    vitals_data = [
        calculate_vital_bands("resting_heart_rate", latest_rhr, rhr_hist),
        calculate_vital_bands("hrv_rmssd", latest_hrv, hrv_hist),
        calculate_vital_bands("respiratory_rate", latest_resp, resp_hist),
        calculate_vital_bands("skin_temp_deviation", latest_temp, temp_hist),
        calculate_vital_bands("spo2_pct", latest_spo2, spo2_hist),
    ]

    vital_items = [VitalBandItem(**item) for item in vitals_data]
    vitals_resp = VitalSignsResponse(
        vitals=vital_items,
        evaluated_at=datetime.now(timezone.utc),
    )

    # Calculate Illness Evaluation
    rhr_z = vitals_data[0].get("z_score")
    hrv_z = vitals_data[1].get("z_score")
    resp_z = vitals_data[2].get("z_score")
    temp_z = vitals_data[3].get("z_score")
    baseline_trusted = vitals_data[0].get("nights_count", 0) >= 14

    illness_data = evaluate_illness(
        rhr_z=rhr_z,
        skin_temp_z=temp_z,
        hrv_z=hrv_z,
        resp_z=resp_z,
        baseline_trusted=baseline_trusted,
    )
    illness_resp = IllnessEvaluationResponse(**illness_data)

    return vitals_resp, illness_resp


@router.get("/vitals", response_model=VitalSignsResponse)
async def get_vital_signs(
    device_id: Optional[str] = Query(None, description="Device identifier"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> VitalSignsResponse:
    """Retrieve 5-metric personal baseline vitals matrix."""
    vitals_resp, _ = await compute_device_vitals_and_illness(db, device_id)
    return vitals_resp


@router.get("/illness-check", response_model=IllnessEvaluationResponse)
async def get_illness_check(
    device_id: Optional[str] = Query(None, description="Device identifier"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> IllnessEvaluationResponse:
    """Evaluate illness anomaly score and early warning status."""
    _, illness_resp = await compute_device_vitals_and_illness(db, device_id)
    return illness_resp
