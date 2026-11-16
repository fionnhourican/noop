"""Device management routes."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Device
from app.schemas.domain import DeviceResponse
from app.security import get_current_dashboard_user

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_dashboard_user),
) -> List[DeviceResponse]:
    """Retrieve all registered WHOOP devices."""
    result = await db.execute(select(Device).order_by(Device.created_at.desc()))
    return list(result.scalars().all())
