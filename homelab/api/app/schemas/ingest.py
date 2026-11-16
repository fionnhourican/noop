"""Pydantic schemas for the batch ingestion protocol."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestRecord(BaseModel):
    """Individual observation record within an ingestion batch."""
    record_id: str = Field(..., description="Globally unique record ID (UUID)")
    type: str = Field(..., description="Record type: heart_rate, biometric, raw_frame, collector_status, etc.")
    timestamp: datetime = Field(..., description="Observation timestamp (UTC)")
    reception_timestamp: Optional[datetime] = Field(None, description="Time when collector received the frame")
    data_origin: str = Field("live", description="Data origin: 'live' or 'historical'")
    validation_status: str = Field("valid", description="Integrity status: 'valid', 'suspect', or 'raw'")
    protocol_version: int = Field(4, description="Protocol generation (4 for WHOOP 4.0)")
    decoder_version: str = Field("1.0.0", description="Decoder version string")

    # Raw frame reference if available
    raw_frame_hex: Optional[str] = Field(None, description="Hex representation of source BLE frame")
    char_uuid: Optional[str] = Field(None, description="Originating GATT characteristic UUID")
    inner_type: Optional[int] = Field(None, description="Inner packet type (40, 47, 48, 49)")

    # Biometric values
    value: Optional[Any] = Field(None, description="Primary scalar measurement or structured dictionary")
    unit: Optional[str] = Field(None, description="Measurement unit (bpm, ms, celsius, g, etc.)")
    source: Optional[str] = Field(None, description="Sensor source (whoop_ble, historical, ground_truth)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extensible telemetry or sub-measurements")


class IngestBatchRequest(BaseModel):
    """Payload for POST /api/v1/ingest/batches."""
    schema_version: int = Field(1, description="Batch payload schema version")
    device_id: str = Field(..., description="Originating device identifier")
    batch_id: str = Field(..., description="Unique batch identifier for idempotency")
    records: List[IngestRecord] = Field(..., description="Array of observation records")


class IngestBatchResponse(BaseModel):
    """Response returned upon successful transactional batch ingestion."""
    status: str = "success"
    batch_id: str
    accepted: int
    duplicates: int
    rejected: int
    message: str = "Batch processed successfully"
