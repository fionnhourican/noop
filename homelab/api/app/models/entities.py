"""SQLAlchemy models for NOOP Home Lab."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Device(Base):
    """Registered WHOOP straps."""
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=True)
    model = Column(String(32), default="whoop4", nullable=False)
    serial = Column(String(64), nullable=True)
    firmware_version = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class SyncBatch(Base):
    """Metadata for uploaded synchronization batches."""
    __tablename__ = "sync_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(String(64), unique=True, nullable=False, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    schema_version = Column(Integer, default=1, nullable=False)
    records_count = Column(Integer, default=0, nullable=False)
    accepted_count = Column(Integer, default=0, nullable=False)
    duplicate_count = Column(Integer, default=0, nullable=False)
    rejected_count = Column(Integer, default=0, nullable=False)
    received_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class RawFrame(Base):
    """Immutable raw Bluetooth LE frames for auditing and re-decoding."""
    __tablename__ = "raw_frames"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(64), nullable=False, index=True)
    recv_ms = Column(BigInteger, nullable=False)
    char_uuid = Column(String(64), nullable=False)
    inner_type = Column(Integer, nullable=True, index=True)
    frame_hex = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("device_id", "frame_hex", name="uq_raw_frame_dev_hex"),
        Index("idx_raw_frame_dev_recv", "device_id", "recv_ms"),
    )


class SourceRecord(Base):
    """Provenance tracking for every ingested observation."""
    __tablename__ = "source_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_record_id = Column(String(128), unique=True, nullable=False, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    batch_id = Column(String(64), nullable=False, index=True)
    observation_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    reception_timestamp = Column(DateTime(timezone=True), nullable=False)
    raw_source_frame_id = Column(UUID(as_uuid=True), ForeignKey("raw_frames.id", ondelete="SET NULL"), nullable=True)
    protocol_version = Column(Integer, default=4, nullable=False)
    decoder_version = Column(String(32), default="1.0.0", nullable=False)
    record_type = Column(String(64), nullable=False, index=True)
    data_origin = Column(String(16), default="live", nullable=False)  # "live" | "historical"
    validation_status = Column(String(16), default="valid", nullable=False)  # "valid" | "suspect" | "raw"
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class HeartRateSample(Base):
    """Normalized per-second heart rate readings."""
    __tablename__ = "heart_rate_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_record_id = Column(String(128), ForeignKey("source_records.source_record_id", ondelete="CASCADE"), nullable=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    bpm = Column(Integer, nullable=False)
    source = Column(String(32), default="whoop_ble", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("device_id", "timestamp", name="uq_hr_sample_dev_time"),
    )


class BiometricRecord(Base):
    """Rich per-second biometrics (R-R intervals, motion gravity, optical ADC, temperature)."""
    __tablename__ = "biometric_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_record_id = Column(String(128), ForeignKey("source_records.source_record_id", ondelete="CASCADE"), nullable=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    rr_count = Column(Integer, nullable=True)
    rr_mean_ms = Column(Float, nullable=True)
    rmssd = Column(Float, nullable=True)
    gravity_x = Column(Float, nullable=True)
    gravity_y = Column(Float, nullable=True)
    gravity_z = Column(Float, nullable=True)
    spo2_red = Column(Integer, nullable=True)
    spo2_ir = Column(Integer, nullable=True)
    spo2_pct = Column(Float, nullable=True)
    skin_temp_raw = Column(Integer, nullable=True)
    skin_temp_c = Column(Float, nullable=True)
    resp_rate_raw = Column(Integer, nullable=True)
    respiratory_rate = Column(Float, nullable=True)
    record_version = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("device_id", "timestamp", name="uq_biometric_dev_time"),
    )


class SleepSession(Base):
    """Computed sleep periods and stage summaries."""
    __tablename__ = "sleep_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_seconds = Column(Integer, nullable=False)
    deep_seconds = Column(Integer, nullable=True)
    light_seconds = Column(Integer, nullable=True)
    rem_seconds = Column(Integer, nullable=True)
    wake_seconds = Column(Integer, nullable=True)
    sleep_efficiency = Column(Float, nullable=True)
    algorithm_version = Column(String(32), default="1.0.0", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    stages = relationship("SleepStage", back_populates="session", cascade="all, delete-orphan")


class SleepStage(Base):
    """Detailed sleep stage intervals within a session."""
    __tablename__ = "sleep_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sleep_session_id = Column(UUID(as_uuid=True), ForeignKey("sleep_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(16), nullable=False)  # "wake", "light", "deep", "rem"
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)

    session = relationship("SleepSession", back_populates="stages")


class RecoveryMetric(Base):
    """Daily recovery scores and baselines."""
    __tablename__ = "recovery_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_id = Column(String(64), unique=True, nullable=False, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    recovery_score = Column(Float, nullable=False)  # 0.0 - 100.0
    hrv_rmssd = Column(Float, nullable=False)
    resting_heart_rate = Column(Float, nullable=False)
    respiratory_rate = Column(Float, nullable=True)
    skin_temp_deviation = Column(Float, nullable=True)
    sleep_performance = Column(Float, nullable=True)
    algorithm_version = Column(String(32), default="noop_recovery_v1", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("device_id", "date", name="uq_recovery_dev_date"),
    )


class StrainMetric(Base):
    """Daily day strain scores computed from heart rate intervals."""
    __tablename__ = "strain_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_id = Column(String(64), unique=True, nullable=False, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    strain_score = Column(Float, nullable=False)  # 0.0 - 21.0
    average_hr = Column(Float, nullable=True)
    max_hr = Column(Integer, nullable=True)
    kilojoules = Column(Float, nullable=True)
    algorithm_version = Column(String(32), default="noop_strain_banister_v1", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("device_id", "date", name="uq_strain_dev_date"),
    )


class Workout(Base):
    """Detected or logged workout sessions."""
    __tablename__ = "workouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_id = Column(String(64), unique=True, nullable=False, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    sport_name = Column(String(64), default="Activity", nullable=False)
    strain_score = Column(Float, nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    max_heart_rate = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class CollectorStatus(Base):
    """Latest status telemetry reported by the Windows collector agent."""
    __tablename__ = "collector_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(64), unique=True, nullable=False, index=True)
    last_seen = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    connection_state = Column(String(32), default="connected", nullable=False)
    battery_percentage = Column(Float, nullable=True)
    battery_millivolts = Column(Integer, nullable=True)
    is_charging = Column(Boolean, nullable=True)
    queued_records = Column(Integer, default=0, nullable=False)
    last_sync_timestamp = Column(DateTime(timezone=True), nullable=True)
    agent_version = Column(String(32), default="1.0.0", nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
