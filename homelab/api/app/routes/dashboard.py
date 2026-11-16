"""Dashboard aggregate summary route."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.entities import (
    BiometricRecord,
    CollectorStatus,
    Device,
    HeartRateSample,
    RecoveryMetric,
    SleepSession,
    StrainMetric,
    SyncBatch,
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
from app.services.analytics import (
    calculate_banister_trimp,
    calculate_recovery_score,
    trimp_to_strain,
)

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

    # Compute Strain on the fly if missing but samples exist
    if not latest_strain and latest_hr:
        dev_id = latest_hr.device_id
        d = latest_hr.timestamp.date()
        start_dt = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(d, datetime.max.time(), tzinfo=timezone.utc)
        samples_q = select(HeartRateSample.bpm).where(
            HeartRateSample.device_id == dev_id,
            HeartRateSample.timestamp >= start_dt,
            HeartRateSample.timestamp <= end_dt,
        )
        bpms = list((await db.execute(samples_q)).scalars().all())
        if bpms:
            trimp = sum(calculate_banister_trimp(b) for b in bpms)
            strain_val = trimp_to_strain(trimp)
            avg_hr = round(sum(bpms) / len(bpms), 1)
            max_hr = max(bpms)
            strain_stmt = (
                pg_insert(StrainMetric)
                .values(
                    metric_id=f"strain_{dev_id}_{d.isoformat()}",
                    device_id=dev_id,
                    date=d,
                    strain_score=strain_val,
                    average_hr=avg_hr,
                    max_hr=max_hr,
                    algorithm_version="noop_strain_banister_v1",
                )
                .on_conflict_do_update(
                    index_elements=["device_id", "date"],
                    set_={
                        "strain_score": strain_val,
                        "average_hr": avg_hr,
                        "max_hr": max_hr,
                    },
                )
            )
            await db.execute(strain_stmt)
            await db.commit()
            latest_strain = (await db.execute(str_q.order_by(StrainMetric.date.desc()).limit(1))).scalars().first()

    # Compute Recovery on the fly if missing but samples exist
    if not latest_rec and latest_hr:
        dev_id = latest_hr.device_id
        d = latest_hr.timestamp.date()
        start_dt = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(d, datetime.max.time(), tzinfo=timezone.utc)
        samples_q = select(HeartRateSample.bpm).where(
            HeartRateSample.device_id == dev_id,
            HeartRateSample.timestamp >= start_dt,
            HeartRateSample.timestamp <= end_dt,
        )
        bpms = list((await db.execute(samples_q)).scalars().all())
        if bpms:
            bio_q = select(BiometricRecord.rmssd).where(
                BiometricRecord.device_id == dev_id,
                BiometricRecord.timestamp >= start_dt,
                BiometricRecord.timestamp <= end_dt,
                BiometricRecord.rmssd.isnot(None),
            )
            rmssds = [r for r in (await db.execute(bio_q)).scalars().all() if r is not None]
            hrv = round(sum(rmssds) / len(rmssds), 1) if rmssds else 65.0
            rhr = float(min(bpms))
            rec_score, _ = calculate_recovery_score(hrv_rmssd=hrv, resting_hr=rhr)
            rec_stmt = (
                pg_insert(RecoveryMetric)
                .values(
                    metric_id=f"recovery_{dev_id}_{d.isoformat()}",
                    device_id=dev_id,
                    date=d,
                    recovery_score=rec_score,
                    hrv_rmssd=hrv,
                    resting_heart_rate=rhr,
                    algorithm_version="noop_recovery_v1",
                )
                .on_conflict_do_update(
                    index_elements=["device_id", "date"],
                    set_={
                        "recovery_score": rec_score,
                        "hrv_rmssd": hrv,
                        "resting_heart_rate": rhr,
                    },
                )
            )
            await db.execute(rec_stmt)
            await db.commit()
            latest_rec = (await db.execute(rec_q.order_by(RecoveryMetric.date.desc()).limit(1))).scalars().first()

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

    # Fall back to latest SyncBatch if collector status is not yet saved
    if not latest_col:
        batch_q = select(SyncBatch)
        if device_id:
            batch_q = batch_q.where(SyncBatch.device_id == device_id)
        batch_res = await db.execute(batch_q.order_by(SyncBatch.received_at.desc()).limit(1))
        last_batch = batch_res.scalars().first()
        if last_batch:
            dev_id = last_batch.device_id
            latest_col = CollectorStatus(
                device_id=dev_id,
                last_seen=last_batch.received_at,
                connection_state="connected",
                battery_percentage=10.0,
                queued_records=0,
                last_sync_timestamp=last_batch.received_at,
                agent_version="1.0.0",
            )
            db.add(latest_col)
            await db.commit()
            await db.refresh(latest_col)

    return DashboardSummaryResponse(
        latest_heart_rate=HeartRateResponse.model_validate(latest_hr) if latest_hr else None,
        latest_recovery=RecoveryResponse.model_validate(latest_rec) if latest_rec else None,
        latest_strain=StrainResponse.model_validate(latest_strain) if latest_strain else None,
        latest_sleep=SleepSessionResponse.model_validate(latest_sleep) if latest_sleep else None,
        collector_status=CollectorStatusResponse.model_validate(latest_col) if latest_col else None,
    )
