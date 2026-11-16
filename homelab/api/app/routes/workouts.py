"""Workout activity routes."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Workout
from app.schemas.domain import WorkoutResponse
from app.security import get_current_dashboard_user

router = APIRouter(prefix="/workouts", tags=["Workouts"])


@router.get("", response_model=List[WorkoutResponse])
async def get_workouts(
    device_id: Optional[str] = Query(None, description="Device identifier"),
    start_time: Optional[datetime] = Query(None, description="Start date/time"),
    end_time: Optional[datetime] = Query(None, description="End date/time"),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> List[WorkoutResponse]:
    """Retrieve recorded workout sessions."""
    query = select(Workout)

    if device_id:
        query = query.where(Workout.device_id == device_id)
    if start_time:
        query = query.where(Workout.start_time >= start_time)
    if end_time:
        query = query.where(Workout.end_time <= end_time)

    query = query.order_by(Workout.start_time.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())
