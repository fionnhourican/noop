"""Pydantic response models for query and dashboard endpoints."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    name: Optional[str] = None
    model: str
    serial: Optional[str] = None
    firmware_version: Optional[str] = None
    created_at: datetime


class HeartRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    bpm: int
    source: str


class BiometricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    rr_count: Optional[int] = None
    rr_mean_ms: Optional[float] = None
    rmssd: Optional[float] = None
    gravity_x: Optional[float] = None
    gravity_y: Optional[float] = None
    gravity_z: Optional[float] = None
    spo2_pct: Optional[float] = None
    skin_temp_c: Optional[float] = None
    respiratory_rate: Optional[float] = None


class SleepStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int


class SleepSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    device_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    deep_seconds: Optional[int] = None
    light_seconds: Optional[int] = None
    rem_seconds: Optional[int] = None
    wake_seconds: Optional[int] = None
    sleep_efficiency: Optional[float] = None
    stages: List[SleepStageResponse] = []


class RecoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    recovery_score: float
    hrv_rmssd: float
    resting_heart_rate: float
    respiratory_rate: Optional[float] = None
    skin_temp_deviation: Optional[float] = None
    sleep_performance: Optional[float] = None
    algorithm_version: str


class StrainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    strain_score: float
    average_hr: Optional[float] = None
    max_hr: Optional[int] = None
    kilojoules: Optional[float] = None
    algorithm_version: str


class WorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workout_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    sport_name: str
    strain_score: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None


class CollectorStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    last_seen: datetime
    connection_state: str
    battery_percentage: Optional[float] = None
    battery_millivolts: Optional[int] = None
    is_charging: Optional[bool] = None
    queued_records: int
    last_sync_timestamp: Optional[datetime] = None
    agent_version: str


class DashboardSummaryResponse(BaseModel):
    latest_heart_rate: Optional[HeartRateResponse] = None
    latest_recovery: Optional[RecoveryResponse] = None
    latest_strain: Optional[StrainResponse] = None
    latest_sleep: Optional[SleepSessionResponse] = None
    collector_status: Optional[CollectorStatusResponse] = None
