"""Sleep sessions and staging routes."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.entities import SleepSession
from app.schemas.domain import SleepSessionResponse
from app.security import get_current_dashboard_user

router = APIRouter(prefix="/sleep", tags=["Sleep"])


@router.get("", response_model=List[SleepSessionResponse])
async def get_sleep_sessions(
    device_id: Optional[str] = Query(None, description="Device identifier"),
    start_time: Optional[datetime] = Query(None, description="Start range"),
    end_time: Optional[datetime] = Query(None, description="End range"),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> List[SleepSessionResponse]:
    """Retrieve sleep sessions with stage breakdowns."""
    query = select(SleepSession).options(selectinload(SleepSession.stages))

    if device_id:
        query = query.where(SleepSession.device_id == device_id)
    if start_time:
        query = query.where(SleepSession.start_time >= start_time)
    if end_time:
        query = query.where(SleepSession.end_time <= end_time)

    query = query.order_by(SleepSession.start_time.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())
