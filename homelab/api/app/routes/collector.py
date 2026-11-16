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
    now_utc = datetime.now(timezone.utc)
    stmt = select(CollectorStatus).where(CollectorStatus.device_id == payload.device_id)
    result = await db.execute(stmt)
    status_row = result.scalar_one_or_none()

    if not status_row:
        status_row = CollectorStatus(device_id=payload.device_id)
        db.add(status_row)

    status_row.last_seen = now_utc
    status_row.connection_state = payload.connection_state
    status_row.battery_percentage = payload.battery_percentage
    status_row.battery_millivolts = payload.battery_millivolts
    status_row.is_charging = payload.is_charging
    status_row.queued_records = payload.queued_records
    status_row.agent_version = payload.agent_version

    await db.commit()
    await db.refresh(status_row)
    return status_row
