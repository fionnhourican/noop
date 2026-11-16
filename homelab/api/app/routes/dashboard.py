"""Dashboard aggregate summary route."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.entities import (
    CollectorStatus,
    HeartRateSample,
    RecoveryMetric,
    SleepSession,
    StrainMetric,
)
from app.schemas.domain import (
    CollectorStatusResponse,
    DashboardSummaryResponse,
    HeartRateResponse,
    RecoveryResponse,
    SleepSessionResponse,
    StrainResponse,
)
from app.security import get_current_dashboard_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    device_id: Optional[str] = Query(None, description="Device identifier"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> DashboardSummaryResponse:
    """Retrieve the unified dashboard summary for the overview screen."""
    # Latest HR
    hr_q = select(HeartRateSample)
    if device_id:
        hr_q = hr_q.where(HeartRateSample.device_id == device_id)
    hr_res = await db.execute(hr_q.order_by(HeartRateSample.timestamp.desc()).limit(1))
    latest_hr = hr_res.scalars().first()

    # Latest Recovery
    rec_q = select(RecoveryMetric)
    if device_id:
        rec_q = rec_q.where(RecoveryMetric.device_id == device_id)
    rec_res = await db.execute(rec_q.order_by(RecoveryMetric.date.desc()).limit(1))
    latest_rec = rec_res.scalars().first()

    # Latest Strain
    str_q = select(StrainMetric)
    if device_id:
        str_q = str_q.where(StrainMetric.device_id == device_id)
    str_res = await db.execute(str_q.order_by(StrainMetric.date.desc()).limit(1))
    latest_strain = str_res.scalars().first()

    # Latest Sleep
    slp_q = select(SleepSession).options(selectinload(SleepSession.stages))
    if device_id:
        slp_q = slp_q.where(SleepSession.device_id == device_id)
    slp_res = await db.execute(slp_q.order_by(SleepSession.end_time.desc()).limit(1))
    latest_sleep = slp_res.scalars().first()

    # Latest Collector Status
    col_q = select(CollectorStatus)
    if device_id:
        col_q = col_q.where(CollectorStatus.device_id == device_id)
    col_res = await db.execute(col_q.order_by(CollectorStatus.last_seen.desc()).limit(1))
    latest_col = col_res.scalars().first()

    return DashboardSummaryResponse(
        latest_heart_rate=HeartRateResponse.model_validate(latest_hr) if latest_hr else None,
        latest_recovery=RecoveryResponse.model_validate(latest_rec) if latest_rec else None,
        latest_strain=StrainResponse.model_validate(latest_strain) if latest_strain else None,
        latest_sleep=SleepSessionResponse.model_validate(latest_sleep) if latest_sleep else None,
        collector_status=CollectorStatusResponse.model_validate(latest_col) if latest_col else None,
    )
