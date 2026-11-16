"""Integration and unit tests for SyncWorker."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from noop_agent.config import AgentConfig, ServerConfig
from noop_agent.storage.local_db import LocalDatabase
from noop_agent.storage.queue import DurableQueue
from noop_agent.sync.uploader import IngestResult
from noop_agent.sync.worker import SyncWorker


class TestSyncWorker(unittest.TestCase):
    """Test suite for background sync worker with local SQLite queue."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_collector.sqlite"
        self.db = LocalDatabase(self.db_path)
        self.queue = DurableQueue(self.db)

        self.config = AgentConfig(
            server=ServerConfig(
                url="http://127.0.0.1:8080/api/v1",
                batch_size=10,
                sync_interval_seconds=30,
            )
        )
        self.worker = SyncWorker(config=self.config, queue=self.queue)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_sync_worker_drains_pending_batch(self):
        # Enqueue 3 records
        for i in range(3):
            self.queue.enqueue_record(
                device_id="test-strap",
                record_type="heart_rate",
                value=70 + i,
            )

        stats_before = self.queue.get_stats()
        self.assertEqual(stats_before["pending"], 3)
        self.assertEqual(stats_before["synced"], 0)

        # Mock uploader success
        self.worker.uploader.post_batch_async = AsyncMock(
            return_value=IngestResult(
                success=True,
                status_code=200,
                batch_id="mock-batch",
                accepted=3,
                duplicates=0,
                rejected=0,
            )
        )

        # Process one batch
        has_more = asyncio.run(self.worker._process_one_batch())
        self.assertFalse(has_more)  # 3 items < limit of 10

        stats_after = self.queue.get_stats()
        self.assertEqual(stats_after["pending"], 0)
        self.assertEqual(stats_after["in_flight"], 0)
        self.assertEqual(stats_after["synced"], 3)
        self.assertEqual(self.worker.total_synced_records, 3)

    def test_sync_worker_reverts_batch_on_server_failure(self):
        # Enqueue 2 records
        for i in range(2):
            self.queue.enqueue_record(
                device_id="test-strap",
                record_type="heart_rate",
                value=80 + i,
            )

        # Mock uploader 503 Service Unavailable
        self.worker.uploader.post_batch_async = AsyncMock(
            return_value=IngestResult(
                success=False,
                status_code=503,
                batch_id="mock-batch",
                server_error=True,
                error_detail="Database unavailable",
            )
        )

        has_more = asyncio.run(self.worker._process_one_batch())
        self.assertFalse(has_more)

        # Confirm records reverted back to 'pending' to ensure zero data loss
        stats = self.queue.get_stats()
        self.assertEqual(stats["pending"], 2)
        self.assertEqual(stats["in_flight"], 0)
        self.assertEqual(stats["synced"], 0)
        self.assertEqual(self.worker.total_synced_records, 0)
        self.assertEqual(self.worker.backoff.consecutive_failures, 1)

    def test_sync_worker_manual_trigger(self):
        self.assertFalse(self.worker._sync_trigger.is_set())
        self.worker.trigger_sync()
        self.assertTrue(self.worker._sync_trigger.is_set())


if __name__ == "__main__":
    unittest.main()
