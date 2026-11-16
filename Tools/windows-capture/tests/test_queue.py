"""Tests for the durable SQLite queue."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from noop_agent.storage.local_db import LocalDatabase
from noop_agent.storage.queue import DurableQueue


def test_enqueue_and_pull_batch():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_queue.sqlite"
        db = LocalDatabase(db_path)
        q = DurableQueue(db)

        now = datetime.now(timezone.utc)

        # 1. Enqueue raw frame and record
        f_id = q.enqueue_raw_frame("whoop-4-local", b"\xaa\x05\x00\x01\x02\x03\x04\x05")
        r_id1 = q.enqueue_record(
            "whoop-4-local", "heart_rate", now, value=72, raw_frame_id=f_id
        )
        r_id2 = q.enqueue_record(
            "whoop-4-local", "battery", now, value=85, unit="percent"
        )

        assert f_id is not None
        assert r_id1 is not None
        assert r_id2 is not None

        stats = q.get_stats()
        assert stats["pending"] == 2
        assert stats["in_flight"] == 0
        assert stats["synced"] == 0

        # 2. Pull pending batch
        batch_id, batch_records = q.get_pending_batch(limit=10)
        assert batch_id is not None
        assert len(batch_records) == 2

        # 3. Check stats after pull (should be in_flight)
        stats = q.get_stats()
        assert stats["pending"] == 0
        assert stats["in_flight"] == 2

        # 4. Simulate failed delivery -> revert batch
        q.revert_batch(batch_id)
        stats = q.get_stats()
        assert stats["pending"] == 2
        assert stats["in_flight"] == 0

        # 5. Pull batch again and acknowledge success
        batch_id_2, batch_records_2 = q.get_pending_batch(limit=10)
        assert batch_id_2 is not None
        q.acknowledge_batch(batch_id_2, response_payload={"status": "success", "accepted": 2})

        stats = q.get_stats()
        assert stats["pending"] == 0
        assert stats["in_flight"] == 0
        assert stats["synced"] == 2

        db.close()


def test_recover_in_flight_on_startup():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "crash_test.sqlite"
        db = LocalDatabase(db_path)
        q = DurableQueue(db)

        # Enqueue record and mark in_flight
        now = datetime.now(timezone.utc)
        q.enqueue_record("whoop-4-local", "heart_rate", now, value=80)
        batch_id, _ = q.get_pending_batch(limit=10)
        assert q.get_stats()["in_flight"] == 1

        # Simulate agent crash and restart
        db.close()
        db_recovered = LocalDatabase(db_path)
        q_recovered = DurableQueue(db_recovered)

        recovered_count = q_recovered.recover_in_flight()
        assert recovered_count == 1
        assert q_recovered.get_stats()["pending"] == 1
        assert q_recovered.get_stats()["in_flight"] == 0

        db_recovered.close()
