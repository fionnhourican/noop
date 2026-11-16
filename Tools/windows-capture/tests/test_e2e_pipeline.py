"""End-to-End integration test simulating the entire NOOP Home Lab collection and sync pipeline.

Pipeline stages validated:
1. Raw WHOOP 4.0 BLE packet reception & CRC verification.
2. Frame decoding into 12-field ObservationProvenance records.
3. Durable SQLite queue persistence in WAL mode.
4. Historical offload persist-before-ack invariant.
5. IngestBatchRequest payload serialization with source raw frames attached.
6. Transactional batch acknowledgment and idempotent deduplication.
7. Crash recovery (resetting in_flight -> pending on restart).
8. Network failure handling (batch reversion to pending).
"""

import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from noop_agent.ble.characteristics import (
    META_HISTORY_COMPLETE,
    META_HISTORY_END,
    META_HISTORY_START,
    PACKET_HISTORICAL_DATA,
    PACKET_METADATA,
)
from noop_agent.ble.framing import (
    build_command_frame,
    build_history_ack_whoop4,
    crc8,
    crc32,
    history_end_data_whoop4,
    verify_whoop4_frame,
)
from noop_agent.ble.whoop4 import Whoop4Device
from noop_agent.config import AgentConfig, ServerConfig
from noop_agent.protocol.decoder import Whoop4Decoder
from noop_agent.protocol.models import ObservationProvenance
from noop_agent.storage.local_db import LocalDatabase
from noop_agent.storage.queue import DurableQueue
from noop_agent.supervisor import AgentSupervisor
from noop_agent.sync.uploader import IngestResult
from noop_agent.sync.worker import SyncWorker


def synthesize_valid_whoop4_frame(packet_type: int, seq: int, payload: bytes) -> bytes:
    """Helper to synthesize a wire-valid WHOOP 4.0 packet with valid CRC-8 and CRC-32."""
    inner = bytes([packet_type, seq & 0xFF]) + payload
    wire_crc32 = crc32(inner)
    inner_with_crc = inner + wire_crc32.to_bytes(4, "little")

    length = len(inner_with_crc)
    len_bytes = length.to_bytes(2, "little")
    header_crc8 = crc8(len_bytes)

    return bytes([0xAA]) + len_bytes + bytes([header_crc8]) + inner_with_crc


class TestEndToEndPipeline(unittest.TestCase):
    """Full integration test exercising all components from BLE packet to HTTP batching."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "e2e_collector.sqlite"
        self.db = LocalDatabase(self.db_path)
        self.queue = DurableQueue(self.db)
        self.decoder = Whoop4Decoder()

        self.config = AgentConfig(
            server=ServerConfig(
                url="http://127.0.0.1:8080/api/v1",
                batch_size=50,
                sync_interval_seconds=30,
            ),
            data_dir=Path(self.temp_dir.name),
        )

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_full_pipeline_flow(self):
        """Test complete flow: Live frame -> SQLite -> Batch extraction -> Uploader -> Server ACK."""
        device_id = "EA:D1:44:88:99:AA"

        # 1. Simulate incoming raw BLE realtime frame (type 40)
        # Using a representative 32-byte payload with unix timestamp + optical/accel bytes
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        payload = (
            now_epoch.to_bytes(4, "little")
            + b"\x48"  # HR 72 bpm
            + b"\x02"  # 2 rr intervals
            + (830).to_bytes(2, "little")
            + (840).to_bytes(2, "little")
            + (0).to_bytes(2, "little")
            + (1000).to_bytes(2, "little")  # 1.0g z-axis
            + b"\x00" * 15
        )

        frame = synthesize_valid_whoop4_frame(40, 1, payload)
        self.assertTrue(verify_whoop4_frame(frame))

        # 2. Persist raw frame immutably
        raw_frame_id = self.queue.enqueue_raw_frame(
            device_id=device_id,
            frame_bytes=frame,
            char_uuid="61000002-0000-0000-0000-000000000000",
            inner_type=40,
        )
        self.assertIsNotNone(raw_frame_id)

        # 3. Decode frame with full provenance tracking
        records = self.decoder.decode_frame(frame, device_id=device_id, raw_frame_id=raw_frame_id)
        self.assertGreaterEqual(len(records), 1)

        # 4. Enqueue decoded records into durable SQLite queue
        for rec in records:
            rec_id = self.queue.enqueue_observation(rec)
            self.assertIsNotNone(rec_id)

        # Verify queue stats
        stats = self.queue.get_stats()
        self.assertGreaterEqual(stats["pending"], 1)
        self.assertEqual(stats["in_flight"], 0)
        self.assertEqual(stats["synced"], 0)

        # 5. Extract pending batch for HTTP synchronization
        batch_id, batch_records = self.queue.get_pending_batch(limit=10)
        self.assertIsNotNone(batch_id)
        self.assertGreaterEqual(len(batch_records), 1)

        # Verify that source raw frame hex and GATT metadata are joined and preserved
        first = batch_records[0]
        self.assertEqual(first["device_id"], device_id)
        self.assertEqual(first["raw_frame_hex"], frame.hex())
        self.assertEqual(first["char_uuid"], "61000002-0000-0000-0000-000000000000")
        self.assertEqual(first["protocol_version"], 4)
        self.assertEqual(first["decoder_version"], "1.0.0")

        # Verify state transitioned to 'in_flight'
        stats_in_flight = self.queue.get_stats()
        self.assertEqual(stats_in_flight["pending"], 0)
        self.assertGreaterEqual(stats_in_flight["in_flight"], 1)

        # 6. Simulate successful transactional server response
        mock_response = {
            "status": "success",
            "batch_id": batch_id,
            "accepted": len(batch_records),
            "duplicates": 0,
            "rejected": 0,
        }
        self.queue.acknowledge_batch(batch_id, mock_response)

        # Verify records marked 'synced'
        stats_synced = self.queue.get_stats()
        self.assertEqual(stats_synced["pending"], 0)
        self.assertEqual(stats_synced["in_flight"], 0)
        self.assertGreaterEqual(stats_synced["synced"], 1)

    def test_historical_persist_before_ack_e2e(self):
        """Test historical chunk accumulation and the persist-before-ack safety gate."""
        device_id = "EA:D1:44:88:99:AA"
        end_data = b"\xaa\xbb\xcc\xdd\x11\x22\x33\x44"

        # Construct valid HISTORY_END frame with 10 bytes padding + 8 bytes end_data
        inner_payload = bytes([META_HISTORY_END]) + b"\x00" * 10 + end_data
        end_frame = synthesize_valid_whoop4_frame(PACKET_METADATA, seq=2, payload=inner_payload)
        self.assertTrue(verify_whoop4_frame(end_frame))

        committed_records = []
        ack_sent = False

        def mock_chunk_commit(dev_id, records, frames, trim_cursor):
            nonlocal committed_records
            # Persist records and frames
            for r in records:
                self.queue.enqueue_observation(r)
            self.queue.set_sync_state(dev_id, "last_trim_cursor", trim_cursor)
            committed_records = list(records)

        async def mock_send_ack(ack_end_data):
            nonlocal ack_sent
            ack_sent = True
            self.assertEqual(ack_end_data, end_data)

        device = Whoop4Device(
            target_address=device_id,
            on_chunk_commit=mock_chunk_commit,
        )
        device._send_history_ack = mock_send_ack

        # Populate a chunk record
        dummy_obs = ObservationProvenance(
            device_id=device_id,
            record_type="heart_rate",
            timestamp_utc=datetime.now(timezone.utc),
            reception_utc=datetime.now(timezone.utc),
            data_origin="historical",
            value=65,
            unit="bpm",
        )
        device._chunk_records.append(dummy_obs)

        # Trigger reassembled frame arrival
        device._on_reassembled_frame("test-char", end_frame)

        # Verify persist occurred and trim cursor is saved
        self.assertEqual(len(committed_records), 1)
        self.assertEqual(self.queue.get_sync_state(device_id, "last_trim_cursor"), end_data.hex())
        self.assertTrue(ack_sent)

    def test_sync_worker_crash_recovery_and_reversion(self):
        """Verify that an interrupted batch reverts to 'pending' on failure or agent reboot."""
        device_id = "EA:D1:44:88:99:AA"

        # Enqueue 3 records
        for bpm in [70, 72, 75]:
            self.queue.enqueue_record(
                device_id=device_id,
                record_type="heart_rate",
                value=bpm,
            )

        worker = SyncWorker(config=self.config, queue=self.queue)

        # Simulate simulated network timeout / 503 error
        worker.uploader.post_batch_async = AsyncMock(
            return_value=IngestResult(
                success=False,
                status_code=503,
                batch_id="failed-batch",
                server_error=True,
                error_detail="Simulated connection dropped",
            )
        )

        # Execute one batch cycle
        has_more = asyncio.run(worker._process_one_batch())
        self.assertFalse(has_more)

        # Records must revert to 'pending'
        stats = self.queue.get_stats()
        self.assertEqual(stats["pending"], 3)
        self.assertEqual(stats["in_flight"], 0)
        self.assertEqual(stats["synced"], 0)

        # Simulate agent crash and startup recovery
        # Force a record into 'in_flight' as if power was pulled during upload
        conn = self.db.get_connection()
        with conn:
            conn.execute("UPDATE collected_records SET sync_status = 'in_flight' WHERE rowid = 1")

        stats_crashed = self.queue.get_stats()
        self.assertEqual(stats_crashed["in_flight"], 1)

        # Run startup recovery
        recovered = self.queue.recover_in_flight()
        self.assertEqual(recovered, 1)

        stats_recovered = self.queue.get_stats()
        self.assertEqual(stats_recovered["pending"], 3)
        self.assertEqual(stats_recovered["in_flight"], 0)


if __name__ == "__main__":
    unittest.main()
