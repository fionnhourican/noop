"""Initial database schema for NOOP Home Lab.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-11-16 19:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. devices
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column("model", sa.String(32), nullable=False, server_default="whoop4"),
        sa.Column("serial", sa.String(64), nullable=True),
        sa.Column("firmware_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_devices_device_id", "devices", ["device_id"])

    # 2. sync_batches
    op.create_table(
        "sync_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", sa.String(64), unique=True, nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("records_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sync_batches_batch_id", "sync_batches", ["batch_id"])
    op.create_index("ix_sync_batches_device_id", "sync_batches", ["device_id"])

    # 3. raw_frames (immutable)
    op.create_table(
        "raw_frames",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("recv_ms", sa.BigInteger(), nullable=False),
        sa.Column("char_uuid", sa.String(64), nullable=False),
        sa.Column("inner_type", sa.Integer(), nullable=True),
        sa.Column("frame_hex", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "frame_hex", name="uq_raw_frame_dev_hex"),
    )
    op.create_index("ix_raw_frames_device_id", "raw_frames", ["device_id"])
    op.create_index("ix_raw_frames_inner_type", "raw_frames", ["inner_type"])
    op.create_index("idx_raw_frame_dev_recv", "raw_frames", ["device_id", "recv_ms"])

    # 4. source_records (provenance)
    op.create_table(
        "source_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_record_id", sa.String(128), unique=True, nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("batch_id", sa.String(64), nullable=False),
        sa.Column("observation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reception_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_source_frame_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("raw_frames.id", ondelete="SET NULL"), nullable=True),
        sa.Column("protocol_version", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("decoder_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("record_type", sa.String(64), nullable=False),
        sa.Column("data_origin", sa.String(16), nullable=False, server_default="live"),
        sa.Column("validation_status", sa.String(16), nullable=False, server_default="valid"),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_records_source_record_id", "source_records", ["source_record_id"])
    op.create_index("ix_source_records_device_id", "source_records", ["device_id"])
    op.create_index("ix_source_records_batch_id", "source_records", ["batch_id"])
    op.create_index("ix_source_records_obs_time", "source_records", ["observation_timestamp"])
    op.create_index("ix_source_records_record_type", "source_records", ["record_type"])

    # 5. heart_rate_samples
    op.create_table(
        "heart_rate_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_record_id", sa.String(128), sa.ForeignKey("source_records.source_record_id", ondelete="CASCADE"), nullable=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bpm", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="whoop_ble"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "timestamp", name="uq_hr_sample_dev_time"),
    )
    op.create_index("ix_heart_rate_samples_device_id", "heart_rate_samples", ["device_id"])
    op.create_index("ix_heart_rate_samples_timestamp", "heart_rate_samples", ["timestamp"])

    # 6. biometric_records
    op.create_table(
        "biometric_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_record_id", sa.String(128), sa.ForeignKey("source_records.source_record_id", ondelete="CASCADE"), nullable=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rr_count", sa.Integer(), nullable=True),
        sa.Column("rr_mean_ms", sa.Float(), nullable=True),
        sa.Column("rmssd", sa.Float(), nullable=True),
        sa.Column("gravity_x", sa.Float(), nullable=True),
        sa.Column("gravity_y", sa.Float(), nullable=True),
        sa.Column("gravity_z", sa.Float(), nullable=True),
        sa.Column("spo2_red", sa.Integer(), nullable=True),
        sa.Column("spo2_ir", sa.Integer(), nullable=True),
        sa.Column("spo2_pct", sa.Float(), nullable=True),
        sa.Column("skin_temp_raw", sa.Integer(), nullable=True),
        sa.Column("skin_temp_c", sa.Float(), nullable=True),
        sa.Column("resp_rate_raw", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Float(), nullable=True),
        sa.Column("record_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "timestamp", name="uq_biometric_dev_time"),
    )
    op.create_index("ix_biometric_records_device_id", "biometric_records", ["device_id"])
    op.create_index("ix_biometric_records_timestamp", "biometric_records", ["timestamp"])

    # 7. sleep_sessions & 8. sleep_stages
    op.create_table(
        "sleep_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), unique=True, nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("deep_seconds", sa.Integer(), nullable=True),
        sa.Column("light_seconds", sa.Integer(), nullable=True),
        sa.Column("rem_seconds", sa.Integer(), nullable=True),
        sa.Column("wake_seconds", sa.Integer(), nullable=True),
        sa.Column("sleep_efficiency", sa.Float(), nullable=True),
        sa.Column("algorithm_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sleep_sessions_session_id", "sleep_sessions", ["session_id"])
    op.create_index("ix_sleep_sessions_device_id", "sleep_sessions", ["device_id"])
    op.create_index("ix_sleep_sessions_start_time", "sleep_sessions", ["start_time"])
    op.create_index("ix_sleep_sessions_end_time", "sleep_sessions", ["end_time"])

    op.create_table(
        "sleep_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sleep_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sleep_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
    )
    op.create_index("ix_sleep_stages_session_id", "sleep_stages", ["sleep_session_id"])

    # 9. recovery_metrics
    op.create_table(
        "recovery_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_id", sa.String(64), unique=True, nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("recovery_score", sa.Float(), nullable=False),
        sa.Column("hrv_rmssd", sa.Float(), nullable=False),
        sa.Column("resting_heart_rate", sa.Float(), nullable=False),
        sa.Column("respiratory_rate", sa.Float(), nullable=True),
        sa.Column("skin_temp_deviation", sa.Float(), nullable=True),
        sa.Column("sleep_performance", sa.Float(), nullable=True),
        sa.Column("algorithm_version", sa.String(32), nullable=False, server_default="noop_recovery_v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "date", name="uq_recovery_dev_date"),
    )
    op.create_index("ix_recovery_metrics_metric_id", "recovery_metrics", ["metric_id"])
    op.create_index("ix_recovery_metrics_device_id", "recovery_metrics", ["device_id"])
    op.create_index("ix_recovery_metrics_date", "recovery_metrics", ["date"])

    # 10. strain_metrics
    op.create_table(
        "strain_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_id", sa.String(64), unique=True, nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("strain_score", sa.Float(), nullable=False),
        sa.Column("average_hr", sa.Float(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("kilojoules", sa.Float(), nullable=True),
        sa.Column("algorithm_version", sa.String(32), nullable=False, server_default="noop_strain_banister_v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "date", name="uq_strain_dev_date"),
    )
    op.create_index("ix_strain_metrics_metric_id", "strain_metrics", ["metric_id"])
    op.create_index("ix_strain_metrics_device_id", "strain_metrics", ["device_id"])
    op.create_index("ix_strain_metrics_date", "strain_metrics", ["date"])

    # 11. workouts
    op.create_table(
        "workouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workout_id", sa.String(64), unique=True, nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("sport_name", sa.String(64), nullable=False, server_default="Activity"),
        sa.Column("strain_score", sa.Float(), nullable=True),
        sa.Column("avg_heart_rate", sa.Integer(), nullable=True),
        sa.Column("max_heart_rate", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workouts_workout_id", "workouts", ["workout_id"])
    op.create_index("ix_workouts_device_id", "workouts", ["device_id"])
    op.create_index("ix_workouts_start_time", "workouts", ["start_time"])

    # 12. collector_status
    op.create_table(
        "collector_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), unique=True, nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connection_state", sa.String(32), nullable=False, server_default="connected"),
        sa.Column("battery_percentage", sa.Float(), nullable=True),
        sa.Column("battery_millivolts", sa.Integer(), nullable=True),
        sa.Column("is_charging", sa.Boolean(), nullable=True),
        sa.Column("queued_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sync_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("agent_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_collector_status_device_id", "collector_status", ["device_id"])


def downgrade() -> None:
    op.drop_table("collector_status")
    op.drop_table("workouts")
    op.drop_table("strain_metrics")
    op.drop_table("recovery_metrics")
    op.drop_table("sleep_stages")
    op.drop_table("sleep_sessions")
    op.drop_table("biometric_records")
    op.drop_table("heart_rate_samples")
    op.drop_table("source_records")
    op.drop_table("raw_frames")
    op.drop_table("sync_batches")
    op.drop_table("devices")
