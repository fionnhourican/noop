"""Recovery metrics routes."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import RecoveryMetric
from app.schemas.domain import RecoveryResponse
from app.security import get_current_dashboard_user

router = APIRouter(prefix="/recovery", tags=["Recovery"])


@router.get("", response_model=List[RecoveryResponse])
async def get_recovery_metrics(
    device_id: Optional[str] = Query(None, description="Device identifier"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> List[RecoveryResponse]:
    """Retrieve daily recovery metrics."""
    query = select(RecoveryMetric)

    if device_id:
        query = query.where(RecoveryMetric.device_id == device_id)
    if start_date:
        query = query.where(RecoveryMetric.date >= start_date)
    if end_date:
        query = query.where(RecoveryMetric.date <= end_date)

    query = query.order_by(RecoveryMetric.date.desc()).limit(limit)

    result = await db.execute(query)
    return list(reversed(result.scalars().all()))
