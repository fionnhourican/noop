"""Durable local queue for storing and staging records before server sync."""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from noop_agent.storage.local_db import LocalDatabase


def now_ms() -> int:
    return int(time.time() * 1000)


def utc_iso(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()


class DurableQueue:
    """Thread-safe transactional queue on top of LocalDatabase."""

    def __init__(self, db: LocalDatabase):
        self.db = db

    def recover_in_flight(self) -> int:
        """Reset any orphaned 'in_flight' records back to 'pending' on startup."""
        conn = self.db.get_connection()
        with conn:
            cur = conn.execute(
                "UPDATE collected_records SET sync_status = 'pending', batch_id = NULL "
                "WHERE sync_status = 'in_flight'"
            )
            return cur.rowcount

    def enqueue_raw_frame(
        self,
        device_id: str,
        frame: Any = None,
        char_uuid: str = "",
        inner_type: Optional[int] = None,
        recv_ms: Optional[int] = None,
        frame_bytes: Optional[bytes] = None,
        frame_hex: Optional[str] = None,
    ) -> Optional[int]:
        """Store an immutable raw frame (ignores duplicates). Returns rowid or None."""
        if recv_ms is None:
            recv_ms = now_ms()

        raw_bytes = frame if isinstance(frame, bytes) else frame_bytes
        if raw_bytes is not None:
            hex_str = raw_bytes.hex()
            if inner_type is None and len(raw_bytes) > 4:
                inner_type = raw_bytes[4]
        elif isinstance(frame, str):
            hex_str = frame
        elif frame_hex is not None:
            hex_str = frame_hex
        else:
            return None

        conn = self.db.get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO raw_frames(device_id, recv_ms, char_uuid, inner_type, frame_hex) "
                    "VALUES(?, ?, ?, ?, ?) "
                    "ON CONFLICT(device_id, frame_hex) DO NOTHING",
                    (device_id, recv_ms, char_uuid, inner_type, hex_str),
                )
                if cur.rowcount > 0:
                    return cur.lastrowid
                else:
                    row = conn.execute(
                        "SELECT id FROM raw_frames WHERE device_id = ? AND frame_hex = ?",
                        (device_id, hex_str),
                    ).fetchone()
                    return row["id"] if row else None
        except Exception:
            return None

    def enqueue_record(
        self,
        device_id: str,
        record_type: str,
        timestamp: Optional[datetime] = None,
        reception_timestamp: Optional[datetime] = None,
        raw_frame_id: Optional[int] = None,
        protocol_version: int = 4,
        decoder_version: str = "1.0.0",
        data_origin: str = "live",
        validation_status: str = "valid",
        value: Optional[Any] = None,
        unit: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        record_id: Optional[str] = None,
        timestamp_utc: Optional[datetime] = None,
        reception_utc: Optional[datetime] = None,
    ) -> str:
        """Persist a decoded record into the queue with 'pending' status."""
        rec_id = record_id or str(uuid.uuid4())
        ts = timestamp or timestamp_utc or datetime.now(timezone.utc)
        recv_ts = reception_timestamp or reception_utc or datetime.now(timezone.utc)
        rec_time_str = utc_iso(ts)
        recv_time_str = utc_iso(recv_ts)
        val_json = json.dumps(value) if value is not None else None
        meta_json = json.dumps(metadata) if metadata is not None else None

        conn = self.db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO collected_records("
                "  record_id, device_id, record_type, timestamp_utc, reception_utc,"
                "  raw_frame_id, protocol_version, decoder_version, data_origin,"
                "  validation_status, value_json, unit, source, metadata_json,"
                "  sync_status, batch_id, created_ms"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, ?)",
                (
                    rec_id,
                    device_id,
                    record_type,
                    rec_time_str,
                    recv_time_str,
                    raw_frame_id,
                    protocol_version,
                    decoder_version,
                    data_origin,
                    validation_status,
                    val_json,
                    unit,
                    source,
                    meta_json,
                    now_ms(),
                ),
            )
        return rec_id

    def enqueue_observation(self, obs: Any) -> str:
        """Convenience method to enqueue an ObservationProvenance instance."""
        source = obs.metadata.get("source") if getattr(obs, "metadata", None) else None
        return self.enqueue_record(
            device_id=obs.device_id,
            record_type=obs.record_type,
            timestamp=obs.timestamp_utc,
            reception_timestamp=obs.reception_utc,
            raw_frame_id=obs.raw_frame_id,
            protocol_version=obs.protocol_version,
            decoder_version=obs.decoder_version,
            data_origin=obs.data_origin,
            validation_status=obs.validation_status,
            value=obs.value,
            unit=obs.unit,
            source=source,
            metadata=obs.metadata,
        )

    def set_sync_state(self, device_id: str, key: str, value: str) -> None:
        """Store persistent state (e.g. historical trim cursor) in sync_state."""
        conn = self.db.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO sync_state(device_id, k, v) VALUES(?, ?, ?) "
                "ON CONFLICT(device_id, k) DO UPDATE SET v = excluded.v",
                (device_id, key, value),
            )

    def get_sync_state(self, device_id: str, key: str) -> Optional[str]:
        """Retrieve persistent state from sync_state."""
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT v FROM sync_state WHERE device_id = ? AND k = ?",
            (device_id, key),
        ).fetchone()
        return row["v"] if row else None

    def get_pending_batch(
        self,
        limit: int = 100,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Atomically fetch up to `limit` pending records and mark them 'in_flight' under a batch_id."""
        conn = self.db.get_connection()
        batch_id = str(uuid.uuid4())

        with conn:
            rows = conn.execute(
                "SELECT c.record_id, c.device_id, c.record_type, c.timestamp_utc, c.reception_utc,"
                "       c.protocol_version, c.decoder_version, c.data_origin, c.validation_status,"
                "       c.value_json, c.unit, c.source, c.metadata_json,"
                "       r.frame_hex AS raw_frame_hex, r.char_uuid, r.inner_type "
                "FROM collected_records c "
                "LEFT JOIN raw_frames r ON c.raw_frame_id = r.id "
                "WHERE c.sync_status = 'pending' "
                "ORDER BY c.created_ms ASC "
                "LIMIT ?",
                (limit,),
            ).fetchall()

            if not rows:
                return None, []

            record_ids = [r["record_id"] for r in rows]
            placeholders = ",".join("?" * len(record_ids))

            conn.execute(
                f"UPDATE collected_records SET sync_status = 'in_flight', batch_id = ? "
                f"WHERE record_id IN ({placeholders})",
                (batch_id, *record_ids),
            )

            conn.execute(
                "INSERT INTO upload_batches(batch_id, created_ms, records_count, status) "
                "VALUES (?, ?, ?, 'pending')",
                (batch_id, now_ms(), len(record_ids)),
            )

        # Build serialized records
        records = []
        for r in rows:
            val = json.loads(r["value_json"]) if r["value_json"] else None
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else None
            records.append({
                "record_id": r["record_id"],
                "device_id": r["device_id"],
                "type": r["record_type"],
                "timestamp": r["timestamp_utc"],
                "reception_timestamp": r["reception_utc"],
                "protocol_version": r["protocol_version"],
                "decoder_version": r["decoder_version"],
                "data_origin": r["data_origin"],
                "validation_status": r["validation_status"],
                "raw_frame_hex": r["raw_frame_hex"],
                "char_uuid": r["char_uuid"],
                "inner_type": r["inner_type"],
                "value": val,
                "unit": r["unit"],
                "source": r["source"],
                "metadata": meta,
            })

        return batch_id, records

    def acknowledge_batch(self, batch_id: str, response_payload: Optional[Dict[str, Any]] = None) -> None:
        """Mark all records in the batch as successfully synced."""
        conn = self.db.get_connection()
        resp_json = json.dumps(response_payload) if response_payload else None

        with conn:
            conn.execute(
                "UPDATE collected_records SET sync_status = 'synced' "
                "WHERE batch_id = ?",
                (batch_id,),
            )
            conn.execute(
                "UPDATE upload_batches SET status = 'acknowledged', acknowledged_ms = ?, response_json = ? "
                "WHERE batch_id = ?",
                (now_ms(), resp_json, batch_id),
            )

    def revert_batch(self, batch_id: str) -> None:
        """Revert records in an in-flight batch back to 'pending' upon failed delivery."""
        conn = self.db.get_connection()
        with conn:
            conn.execute(
                "UPDATE collected_records SET sync_status = 'pending', batch_id = NULL "
                "WHERE batch_id = ? AND sync_status = 'in_flight'",
                (batch_id,),
            )
            conn.execute(
                "UPDATE upload_batches SET status = 'failed' "
                "WHERE batch_id = ?",
                (batch_id,),
            )

    def get_stats(self) -> Dict[str, int]:
        """Return counts of pending, in_flight, and synced records."""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT sync_status, COUNT(*) as count FROM collected_records GROUP BY sync_status"
        ).fetchall()
        stats = {"pending": 0, "in_flight": 0, "synced": 0, "total": 0}
        for r in rows:
            status_name = r["sync_status"]
            count = r["count"]
            if status_name in stats:
                stats[status_name] = count
            stats["total"] += count
        return stats
