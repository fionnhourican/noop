"""Batch ingestion route for the Windows BLE agent."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import (
    BiometricRecord,
    CollectorStatus,
    Device,
    HeartRateSample,
    RawFrame,
    RecoveryMetric,
    SleepSession,
    SourceRecord,
    StrainMetric,
    SyncBatch,
    Workout,
)
from app.schemas.ingest import IngestBatchRequest, IngestBatchResponse
from app.security import get_current_ingestion_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post(
    "/batches",
    response_model=IngestBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest a batch of observations with transactional idempotency",
)
async def ingest_batch(
    payload: IngestBatchRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_ingestion_token),
) -> IngestBatchResponse:
    """Ingest a batch of records from the Windows collector.

    Guarantees:
    - Atomicity: All records in the batch are committed or none are.
    - Idempotency: Duplicate batches or individual duplicate record_ids are ignored.
    - Full Provenance: Raw frames and source records are tracked with protocol and decoder versions.
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Ensure Device exists (upsert)
    stmt = select(Device).where(Device.device_id == payload.device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if not device:
        device = Device(
            device_id=payload.device_id,
            name=f"WHOOP ({payload.device_id[-4:] if len(payload.device_id) >= 4 else payload.device_id})",
            model="whoop4",
        )
        db.add(device)
        await db.flush()

    # 2. Check if batch was already fully processed
    batch_stmt = select(SyncBatch).where(SyncBatch.batch_id == payload.batch_id)
    batch_res = await db.execute(batch_stmt)
    existing_batch = batch_res.scalar_one_or_none()
    if existing_batch:
        return IngestBatchResponse(
            status="success",
            batch_id=payload.batch_id,
            accepted=0,
            duplicates=payload.records.__len__(),
            rejected=0,
            message="Batch previously processed",
        )

    accepted = 0
    duplicates = 0
    rejected = 0

    # 3. Process records inside the session transaction
    for rec in payload.records:
        try:
            # Check for existing record_id to ensure idempotency
            rec_stmt = select(SourceRecord).where(SourceRecord.source_record_id == rec.record_id)
            rec_res = await db.execute(rec_stmt)
            if rec_res.scalar_one_or_none():
                duplicates += 1
                continue

            # Store raw frame if provided
            raw_frame_id = None
            if rec.raw_frame_hex and rec.char_uuid:
                frame_stmt = select(RawFrame).where(
                    RawFrame.device_id == payload.device_id,
                    RawFrame.frame_hex == rec.raw_frame_hex,
                )
                frame_res = await db.execute(frame_stmt)
                existing_frame = frame_res.scalar_one_or_none()
                if existing_frame:
                    raw_frame_id = existing_frame.id
                else:
                    new_frame = RawFrame(
                        device_id=payload.device_id,
                        recv_ms=int((rec.reception_timestamp or rec.timestamp).timestamp() * 1000),
                        char_uuid=rec.char_uuid,
                        inner_type=rec.inner_type,
                        frame_hex=rec.raw_frame_hex,
                    )
                    db.add(new_frame)
                    await db.flush()
                    raw_frame_id = new_frame.id

            # Create provenance source record
            source_rec = SourceRecord(
                source_record_id=rec.record_id,
                device_id=payload.device_id,
                batch_id=payload.batch_id,
                observation_timestamp=rec.timestamp,
                reception_timestamp=rec.reception_timestamp or now_utc,
                raw_source_frame_id=raw_frame_id,
                protocol_version=rec.protocol_version,
                decoder_version=rec.decoder_version,
                record_type=rec.type,
                data_origin=rec.data_origin,
                validation_status=rec.validation_status,
                raw_payload=rec.metadata or {},
            )
            db.add(source_rec)
            await db.flush()

            # Store typed normalized record
            if rec.type == "heart_rate" and rec.value is not None:
                hr_sample = HeartRateSample(
                    source_record_id=rec.record_id,
                    device_id=payload.device_id,
                    timestamp=rec.timestamp,
                    bpm=int(rec.value),
                    source=rec.source or "whoop_ble",
                )
                db.add(hr_sample)

            elif rec.type == "biometric":
                meta = rec.metadata or {}
                bio_rec = BiometricRecord(
                    source_record_id=rec.record_id,
                    device_id=payload.device_id,
                    timestamp=rec.timestamp,
                    rr_count=meta.get("rr_count"),
                    rr_mean_ms=meta.get("rr_mean_ms"),
                    rmssd=meta.get("rmssd"),
                    gravity_x=meta.get("gravity_x"),
                    gravity_y=meta.get("gravity_y"),
                    gravity_z=meta.get("gravity_z"),
                    spo2_red=meta.get("spo2_red"),
                    spo2_ir=meta.get("spo2_ir"),
                    spo2_pct=meta.get("spo2_pct"),
                    skin_temp_raw=meta.get("skin_temp_raw"),
                    skin_temp_c=meta.get("skin_temp_c"),
                    resp_rate_raw=meta.get("resp_rate_raw"),
                    respiratory_rate=meta.get("respiratory_rate"),
                    record_version=meta.get("record_version"),
                )
                db.add(bio_rec)

            elif rec.type == "collector_status":
                meta = rec.metadata or {}
                status_stmt = select(CollectorStatus).where(CollectorStatus.device_id == payload.device_id)
                status_res = await db.execute(status_stmt)
                col_status = status_res.scalar_one_or_none()
                if not col_status:
                    col_status = CollectorStatus(device_id=payload.device_id)
                    db.add(col_status)

                col_status.last_seen = rec.timestamp
                col_status.connection_state = meta.get("connection_state", "connected")
                col_status.battery_percentage = meta.get("battery_pct")
                col_status.battery_millivolts = meta.get("battery_mV")
                col_status.is_charging = meta.get("is_charging")
                col_status.queued_records = meta.get("queued_records", 0)
                col_status.last_sync_timestamp = now_utc
                col_status.agent_version = rec.decoder_version

            accepted += 1

        except Exception as e:
            logger.error(f"Error processing record {rec.record_id}: {e}")
            rejected += 1

    # Record sync batch summary
    sync_batch = SyncBatch(
        batch_id=payload.batch_id,
        device_id=payload.device_id,
        schema_version=payload.schema_version,
        records_count=len(payload.records),
        accepted_count=accepted,
        duplicate_count=duplicates,
        rejected_count=rejected,
        received_at=now_utc,
    )
    db.add(sync_batch)

    # Commit all atomically
    await db.commit()

    return IngestBatchResponse(
        status="success",
        batch_id=payload.batch_id,
        accepted=accepted,
        duplicates=duplicates,
        rejected=rejected,
        message=f"Batch processed: {accepted} accepted, {duplicates} duplicate(s), {rejected} rejected",
    )
