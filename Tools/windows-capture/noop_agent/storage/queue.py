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
        frame_bytes: bytes,
        char_uuid: str = "",
        inner_type: Optional[int] = None,
        recv_ms: Optional[int] = None,
    ) -> Optional[int]:
        """Store immutable raw BLE frame. Ignores duplicates."""
        if recv_ms is None:
            recv_ms = now_ms()
        frame_hex = frame_bytes.hex()
        conn = self.db.get_connection()
        with conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO raw_frames (device_id, recv_ms, char_uuid, inner_type, frame_hex)
                VALUES (?, ?, ?, ?, ?)
                """,
                (device_id, recv_ms, char_uuid, inner_type, frame_hex),
            )
            if cur.lastrowid:
                return cur.lastrowid
            # Retrieve existing id if duplicate
            row = conn.execute(
                "SELECT id FROM raw_frames WHERE device_id = ? AND frame_hex = ?",
                (device_id, frame_hex),
            ).fetchone()
            return row["id"] if row else None

    def enqueue_record(
        self,
        device_id: str,
        record_type: str,
        timestamp_utc: datetime,
        value: Any,
        unit: Optional[str] = None,
        data_origin: str = "live",
        validation_status: str = "valid",
        protocol_version: int = 4,
        decoder_version: str = "1.0.0",
        raw_frame_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        reception_utc: Optional[datetime] = None,
    ) -> str:
        """Enqueue an observation record for sync."""
        record_id = str(uuid.uuid4())
        created = now_ms()
        t_iso = utc_iso(timestamp_utc)
        r_iso = utc_iso(reception_utc)
        v_json = json.dumps(value) if value is not None else None
        m_json = json.dumps(metadata) if metadata else None

        conn = self.db.get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO collected_records (
                    record_id, device_id, record_type, timestamp_utc, reception_utc,
                    raw_frame_id, protocol_version, decoder_version, data_origin,
                    validation_status, value_json, unit, metadata_json, sync_status, created_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    record_id,
                    device_id,
                    record_type,
                    t_iso,
                    r_iso,
                    raw_frame_id,
                    protocol_version,
                    decoder_version,
                    data_origin,
                    validation_status,
                    v_json,
                    unit,
                    m_json,
                    created,
                ),
            )
        return record_id

    def get_pending_batch(self, limit: int = 100) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Atomically pull and mark a batch of pending records as 'in_flight'."""
        batch_id = str(uuid.uuid4())
        conn = self.db.get_connection()
        with conn:
            rows = conn.execute(
                """
                SELECT record_id, device_id, record_type, timestamp_utc, reception_utc,
                       raw_frame_id, protocol_version, decoder_version, data_origin,
                       validation_status, value_json, unit, metadata_json
                FROM collected_records
                WHERE sync_status = 'pending'
                ORDER BY created_ms ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            if not rows:
                return None, []

            record_ids = [r["record_id"] for r in rows]
            placeholders = ",".join("?" for _ in record_ids)

            conn.execute(
                f"""
                UPDATE collected_records
                SET sync_status = 'in_flight', batch_id = ?
                WHERE record_id IN ({placeholders})
                """,
                [batch_id] + record_ids,
            )

            conn.execute(
                """
                INSERT INTO upload_batches (batch_id, created_ms, records_count, status)
                VALUES (?, ?, ?, 'sent')
                """,
                (batch_id, now_ms(), len(record_ids)),
            )

            results = []
            for r in rows:
                v = json.loads(r["value_json"]) if r["value_json"] else None
                m = json.loads(r["metadata_json"]) if r["metadata_json"] else None
                results.append(
                    {
                        "record_id": r["record_id"],
                        "device_id": r["device_id"],
                        "record_type": r["record_type"],
                        "timestamp_utc": r["timestamp_utc"],
                        "reception_utc": r["reception_utc"],
                        "raw_frame_id": r["raw_frame_id"],
                        "protocol_version": r["protocol_version"],
                        "decoder_version": r["decoder_version"],
                        "data_origin": r["data_origin"],
                        "validation_status": r["validation_status"],
                        "value": v,
                        "unit": r["unit"],
                        "metadata": m,
                    }
                )
            return batch_id, results

    def acknowledge_batch(self, batch_id: str, response_payload: Optional[Dict[str, Any]] = None) -> None:
        """Mark all records in an acknowledged batch as 'synced'."""
        resp_json = json.dumps(response_payload) if response_payload else None
        conn = self.db.get_connection()
        with conn:
            conn.execute(
                """
                UPDATE collected_records
                SET sync_status = 'synced'
                WHERE batch_id = ?
                """,
                (batch_id,),
            )
            conn.execute(
                """
                UPDATE upload_batches
                SET status = 'acknowledged', acknowledged_ms = ?, response_json = ?
                WHERE batch_id = ?
                """,
                (now_ms(), resp_json, batch_id),
            )

    def revert_batch(self, batch_id: str, error_message: Optional[str] = None) -> None:
        """Revert an in_flight batch back to 'pending' on network/server error."""
        conn = self.db.get_connection()
        with conn:
            conn.execute(
                """
                UPDATE collected_records
                SET sync_status = 'pending', batch_id = NULL
                WHERE batch_id = ?
                """,
                (batch_id,),
            )
            conn.execute(
                """
                UPDATE upload_batches
                SET status = 'failed', response_json = ?
                WHERE batch_id = ?
                """,
                (json.dumps({"error": error_message}) if error_message else None, batch_id),
            )

    def get_stats(self) -> Dict[str, int]:
        """Return counts by sync_status."""
        conn = self.db.get_connection()
        counts = {"pending": 0, "in_flight": 0, "synced": 0}
        rows = conn.execute(
            "SELECT sync_status, COUNT(*) as c FROM collected_records GROUP BY sync_status"
        ).fetchall()
        for r in rows:
            st = r["sync_status"]
            if st in counts:
                counts[st] = r["c"]
        return counts
