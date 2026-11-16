"""Collector status and telemetry routes."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import CollectorStatus
from app.schemas.domain import CollectorStatusResponse
from app.security import get_current_dashboard_user, get_current_ingestion_token

router = APIRouter(prefix="/collector", tags=["Collector"])


class CollectorStatusUpdate(BaseModel):
    device_id: str
    connection_state: str = "connected"
    battery_percentage: Optional[float] = None
    battery_millivolts: Optional[int] = None
    is_charging: Optional[bool] = None
    queued_records: int = 0
    agent_version: str = "1.0.0"


@router.get("/status", response_model=CollectorStatusResponse)
async def get_collector_status(
    device_id: Optional[str] = Query(None, description="Device identifier"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> CollectorStatusResponse:
    """Retrieve the latest collector status telemetry."""
    query = select(CollectorStatus)
    if device_id:
        query = query.where(CollectorStatus.device_id == device_id)
    query = query.order_by(CollectorStatus.last_seen.desc())

    result = await db.execute(query)
    status_row = result.scalars().first()
    if not status_row:
        from app.models.entities import SyncBatch
        batch_q = select(SyncBatch)
        if device_id:
            batch_q = batch_q.where(SyncBatch.device_id == device_id)
        batch_res = await db.execute(batch_q.order_by(SyncBatch.received_at.desc()).limit(1))
        last_batch = batch_res.scalars().first()
        if last_batch:
            status_row = CollectorStatus(
                device_id=last_batch.device_id,
                last_seen=last_batch.received_at,
                connection_state="connected",
                battery_percentage=10.0,
                queued_records=0,
                last_sync_timestamp=last_batch.received_at,
                agent_version="1.0.0",
            )
            db.add(status_row)
            await db.commit()
            await db.refresh(status_row)
            return status_row

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collector telemetry available",
        )
    return status_row


@router.post("/status", response_model=CollectorStatusResponse)
async def update_collector_status(
    payload: CollectorStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_ingestion_token),
) -> CollectorStatusResponse:
    """Update collector status from the Windows agent."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    now_utc = datetime.now(timezone.utc)
    stmt = (
        pg_insert(CollectorStatus)
        .values(
            device_id=payload.device_id,
            last_seen=now_utc,
            connection_state=payload.connection_state,
            battery_percentage=payload.battery_percentage,
            battery_millivolts=payload.battery_millivolts,
            is_charging=payload.is_charging,
            queued_records=payload.queued_records,
            agent_version=payload.agent_version,
        )
        .on_conflict_do_update(
            index_elements=["device_id"],
            set_={
                "last_seen": now_utc,
                "connection_state": payload.connection_state,
                "battery_percentage": payload.battery_percentage,
                "battery_millivolts": payload.battery_millivolts,
                "is_charging": payload.is_charging,
                "queued_records": payload.queued_records,
                "agent_version": payload.agent_version,
            },
        )
    )
    await db.execute(stmt)
    await db.commit()

    query = select(CollectorStatus).where(CollectorStatus.device_id == payload.device_id)
    result = await db.execute(query)
    return result.scalar_one()
