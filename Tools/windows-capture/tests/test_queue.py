"""Tests for the durable SQLite queue."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from noop_agent.storage.local_db import LocalDatabase
from noop_agent.storage.queue import DurableQueue


class TestQueue(unittest.TestCase):

    def test_enqueue_and_pull_batch(self):
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

            self.assertIsNotNone(f_id)
            self.assertIsNotNone(r_id1)
            self.assertIsNotNone(r_id2)

            stats = q.get_stats()
            self.assertEqual(stats["pending"], 2)
            self.assertEqual(stats["in_flight"], 0)
            self.assertEqual(stats["synced"], 0)

            # 2. Pull pending batch
            batch_id, batch_records = q.get_pending_batch(limit=10)
            self.assertIsNotNone(batch_id)
            self.assertEqual(len(batch_records), 2)

            # 3. Check stats after pull (should be in_flight)
            stats = q.get_stats()
            self.assertEqual(stats["pending"], 0)
            self.assertEqual(stats["in_flight"], 2)

            # 4. Simulate failed delivery -> revert batch
            q.revert_batch(batch_id)
            stats = q.get_stats()
            self.assertEqual(stats["pending"], 2)
            self.assertEqual(stats["in_flight"], 0)

            # 5. Pull batch again and acknowledge success
            batch_id_2, batch_records_2 = q.get_pending_batch(limit=10)
            self.assertIsNotNone(batch_id_2)
            q.acknowledge_batch(batch_id_2, response_payload={"status": "success", "accepted": 2})

            stats = q.get_stats()
            self.assertEqual(stats["pending"], 0)
            self.assertEqual(stats["in_flight"], 0)
            self.assertEqual(stats["synced"], 2)

            db.close()

    def test_recover_in_flight_on_startup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "crash_test.sqlite"
            db = LocalDatabase(db_path)
            q = DurableQueue(db)

            # Enqueue record and mark in_flight
            now = datetime.now(timezone.utc)
            q.enqueue_record("whoop-4-local", "heart_rate", now, value=80)
            batch_id, _ = q.get_pending_batch(limit=10)
            self.assertEqual(q.get_stats()["in_flight"], 1)

            # Simulate agent crash and restart
            db.close()
            db_recovered = LocalDatabase(db_path)
            q_recovered = DurableQueue(db_recovered)

            recovered_count = q_recovered.recover_in_flight()
            self.assertEqual(recovered_count, 1)
            self.assertEqual(q_recovered.get_stats()["pending"], 1)
            self.assertEqual(q_recovered.get_stats()["in_flight"], 0)

            db_recovered.close()


if __name__ == "__main__":
    unittest.main()
