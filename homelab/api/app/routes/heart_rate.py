"""Heart rate query routes."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import HeartRateSample
from app.schemas.domain import HeartRateResponse
from app.security import get_current_dashboard_user

router = APIRouter(prefix="/heart-rate", tags=["Heart Rate"])


@router.get("", response_model=List[HeartRateResponse])
async def get_heart_rate_samples(
    device_id: Optional[str] = Query(None, description="Filter by device identifier"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (UTC)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (UTC)"),
    limit: int = Query(500, ge=1, le=5000, description="Max samples to return"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> List[HeartRateResponse]:
    """Retrieve historical heart rate samples."""
    query = select(HeartRateSample)

    if device_id:
        query = query.where(HeartRateSample.device_id == device_id)
    if start_time:
        query = query.where(HeartRateSample.timestamp >= start_time)
    if end_time:
        query = query.where(HeartRateSample.timestamp <= end_time)

    query = query.order_by(HeartRateSample.timestamp.desc()).limit(limit)

    result = await db.execute(query)
    samples = result.scalars().all()
    # Return chronologically ascending
    return list(reversed(samples))
