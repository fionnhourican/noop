"""Batch ingestion route for the Windows BLE agent."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
    device_stmt = (
        pg_insert(Device)
        .values(
            device_id=payload.device_id,
            name=f"WHOOP ({payload.device_id[-4:] if len(payload.device_id) >= 4 else payload.device_id})",
            model="whoop4",
        )
        .on_conflict_do_nothing(index_elements=["device_id"])
    )
    await db.execute(device_stmt)

    # 2. Check if batch was already fully processed
    batch_stmt = select(SyncBatch).where(SyncBatch.batch_id == payload.batch_id)
    batch_res = await db.execute(batch_stmt)
    existing_batch = batch_res.scalar_one_or_none()
    if existing_batch:
        return IngestBatchResponse(
            status="success",
            batch_id=payload.batch_id,
            accepted=0,
            duplicates=len(payload.records),
            rejected=0,
            message="Batch previously processed",
        )

    accepted = 0
    duplicates = 0
    rejected = 0

    # 3. Process records inside the session transaction
    for rec in payload.records:
        try:
            async with db.begin_nested():
                # Store raw frame if provided
                raw_frame_id = None
                if rec.raw_frame_hex and rec.char_uuid:
                    frame_stmt = (
                        pg_insert(RawFrame)
                        .values(
                            device_id=payload.device_id,
                            recv_ms=int((rec.reception_timestamp or rec.timestamp).timestamp() * 1000),
                            char_uuid=rec.char_uuid,
                            inner_type=rec.inner_type,
                            frame_hex=rec.raw_frame_hex,
                        )
                        .on_conflict_do_nothing(index_elements=["device_id", "frame_hex"])
                        .returning(RawFrame.id)
                    )
                    frame_res = await db.execute(frame_stmt)
                    raw_frame_id = frame_res.scalar_one_or_none()
                    if not raw_frame_id:
                        sel = select(RawFrame.id).where(
                            RawFrame.device_id == payload.device_id,
                            RawFrame.frame_hex == rec.raw_frame_hex,
                        )
                        raw_frame_id = (await db.execute(sel)).scalar_one_or_none()

                # Create provenance source record (idempotent on source_record_id)
                source_rec_stmt = (
                    pg_insert(SourceRecord)
                    .values(
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
                    .on_conflict_do_nothing(index_elements=["source_record_id"])
                    .returning(SourceRecord.id)
                )
                src_res = await db.execute(source_rec_stmt)
                if not src_res.scalar_one_or_none():
                    duplicates += 1
                    continue

                # Store typed normalized record
                if rec.type == "heart_rate" and rec.value is not None:
                    hr_stmt = (
                        pg_insert(HeartRateSample)
                        .values(
                            source_record_id=rec.record_id,
                            device_id=payload.device_id,
                            timestamp=rec.timestamp,
                            bpm=int(round(float(rec.value))),
                            source=rec.source or "whoop_ble",
                        )
                        .on_conflict_do_nothing(index_elements=["device_id", "timestamp"])
                    )
                    await db.execute(hr_stmt)

                elif rec.type == "biometric":
                    meta = rec.metadata or {}
                    bio_stmt = (
                        pg_insert(BiometricRecord)
                        .values(
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
                        .on_conflict_do_nothing(index_elements=["device_id", "timestamp"])
                    )
                    await db.execute(bio_stmt)

                elif rec.type == "collector_status":
                    meta = rec.metadata or {}
                    col_stmt = (
                        pg_insert(CollectorStatus)
                        .values(
                            device_id=payload.device_id,
                            last_seen=rec.timestamp,
                            connection_state=meta.get("connection_state", "connected"),
                            battery_percentage=meta.get("battery_pct"),
                            battery_millivolts=meta.get("battery_mV"),
                            is_charging=meta.get("is_charging"),
                            queued_records=meta.get("queued_records", 0),
                            last_sync_timestamp=now_utc,
                            agent_version=rec.decoder_version,
                        )
                        .on_conflict_do_update(
                            index_elements=["device_id"],
                            set_={
                                "last_seen": rec.timestamp,
                                "connection_state": meta.get("connection_state", "connected"),
                                "battery_percentage": meta.get("battery_pct"),
                                "battery_millivolts": meta.get("battery_mV"),
                                "is_charging": meta.get("is_charging"),
                                "queued_records": meta.get("queued_records", 0),
                                "last_sync_timestamp": now_utc,
                                "agent_version": rec.decoder_version,
                            },
                        )
                    )
                    await db.execute(col_stmt)

            accepted += 1

        except Exception as e:
            logger.error(f"Error processing record {rec.record_id}: {e}")
            rejected += 1

    # Record sync batch summary
    sync_batch_stmt = (
        pg_insert(SyncBatch)
        .values(
            batch_id=payload.batch_id,
            device_id=payload.device_id,
            schema_version=payload.schema_version,
            records_count=len(payload.records),
            accepted_count=accepted,
            duplicate_count=duplicates,
            rejected_count=rejected,
            received_at=now_utc,
        )
        .on_conflict_do_nothing(index_elements=["batch_id"])
    )
    await db.execute(sync_batch_stmt)

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
