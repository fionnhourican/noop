"""Tests for batch ingestion schema validation and idempotency contracts."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas.ingest import IngestBatchRequest, IngestBatchResponse, IngestRecord


def test_ingest_record_schema():
    now = datetime.now(timezone.utc)
    rec = IngestRecord(
        record_id="rec-12345",
        type="heart_rate",
        timestamp=now,
        value=75,
        unit="bpm",
        data_origin="live",
        validation_status="valid",
    )
    assert rec.record_id == "rec-12345"
    assert rec.value == 75
    assert rec.protocol_version == 4


def test_ingest_batch_request_schema():
    now = datetime.now(timezone.utc)
    rec1 = IngestRecord(
        record_id="rec-1",
        type="heart_rate",
        timestamp=now,
        value=72,
    )
    rec2 = IngestRecord(
        record_id="rec-2",
        type="biometric",
        timestamp=now,
        metadata={"rmssd": 45.2, "gravity_x": 0.0, "gravity_y": 0.0, "gravity_z": 1.0},
    )

    batch = IngestBatchRequest(
        schema_version=1,
        device_id="whoop-4-local",
        batch_id="batch-001",
        records=[rec1, rec2],
    )
    assert batch.device_id == "whoop-4-local"
    assert len(batch.records) == 2


def test_ingest_batch_requires_device_and_records():
    with pytest.raises(ValidationError):
        IngestBatchRequest(
            schema_version=1,
            batch_id="batch-001",
            # Missing device_id and records
        )


def test_ingest_batch_response_schema():
    resp = IngestBatchResponse(
        status="success",
        batch_id="batch-001",
        accepted=10,
        duplicates=2,
        rejected=0,
    )
    assert resp.accepted == 10
    assert resp.duplicates == 2
