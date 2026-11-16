"""Background synchronization worker coordinating durable queue draining and upload."""

import asyncio
import logging
import time
from typing import Callable, Optional

from noop_agent.config import AgentConfig
from noop_agent.storage.queue import DurableQueue
from noop_agent.sync.retry import BackoffManager
from noop_agent.sync.uploader import BatchUploader, IngestResult

logger = logging.getLogger(__name__)


class SyncWorker:
    """Asynchronous worker that drains the local durable SQLite queue to the server."""

    def __init__(
        self,
        config: AgentConfig,
        queue: DurableQueue,
        on_status_change: Optional[Callable[[str, Optional[str]], None]] = None,
    ):
        self.config = config
        self.queue = queue
        self.on_status_change = on_status_change

        token = config.get_ingestion_token()
        self.uploader = BatchUploader(
            server_url=config.server.url,
            token=token,
            timeout_seconds=15.0,
        )
        self.backoff = BackoffManager(
            base_delay=2.0,
            max_delay=60.0,
            factor=2.0,
        )

        self._stop_event = asyncio.Event()
        self._sync_trigger = asyncio.Event()
        self._worker_task: Optional[asyncio.Task] = None

        self.last_sync_time: Optional[float] = None
        self.total_synced_records: int = 0
        self.is_running: bool = False

    def trigger_sync(self) -> None:
        """Trigger an immediate sync cycle from the UI or external event."""
        logger.info("Manual or expedited sync triggered.")
        self._sync_trigger.set()

    def start(self) -> asyncio.Task:
        """Start the background sync worker task."""
        if self.is_running:
            return self._worker_task  # type: ignore

        self.is_running = True
        self._stop_event.clear()
        self._worker_task = asyncio.create_task(self._run_loop())
        return self._worker_task

    async def stop(self) -> None:
        """Gracefully terminate sync worker."""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()
        self._sync_trigger.set()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("Sync worker stopped.")

    async def _run_loop(self) -> None:
        """Main synchronization loop."""
        logger.info(
            "Sync worker started. Target: %s, Interval: %ds, Batch size: %d",
            self.uploader.endpoint_url,
            self.config.server.sync_interval_seconds,
            self.config.server.batch_size,
        )

        while not self._stop_event.is_set():
            # Check if backoff window has elapsed
            if not self.backoff.can_retry_now:
                wait_time = min(self.backoff.remaining_wait, 1.0)
                await asyncio.sleep(wait_time)
                continue

            has_more = await self._process_one_batch()

            # If there's more in the queue and we succeeded, process next batch immediately
            if has_more and not self._stop_event.is_set():
                continue

            # Otherwise, wait for either sync_interval or manual trigger
            try:
                self._sync_trigger.clear()
                await asyncio.wait_for(
                    self._sync_trigger.wait(),
                    timeout=float(self.config.server.sync_interval_seconds),
                )
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break

    async def _process_one_batch(self) -> bool:
        """Fetch and upload one pending batch.

        Returns True if a full batch was processed and more items may be pending.
        """
        limit = self.config.server.batch_size
        batch_id, records = self.queue.get_pending_batch(limit=limit)

        if not batch_id or not records:
            return False

        device_id = records[0].get("device_id") or self.config.device.address or "whoop4"
        logger.info(
            "Uploading batch %s (%d records) for device %s...",
            batch_id,
            len(records),
            device_id,
        )

        result: IngestResult = await self.uploader.post_batch_async(
            batch_id=batch_id,
            device_id=device_id,
            records=records,
        )

        if result.success:
            self.queue.acknowledge_batch(batch_id, result.response_payload)
            self.backoff.record_success()
            self.last_sync_time = time.time()
            self.total_synced_records += len(records)
            logger.info(
                "Batch %s confirmed: %d accepted, %d duplicates (total synced=%d)",
                batch_id,
                result.accepted,
                result.duplicates,
                self.total_synced_records,
            )
            if self.on_status_change:
                self.on_status_change("synced", f"{result.accepted} records synced")

            # Return True if batch was full to continue draining queue
            return len(records) >= limit
        else:
            # Revert batch to 'pending' so no records are lost!
            self.queue.revert_batch(batch_id)
            delay = self.backoff.record_failure(result.retry_after)
            logger.warning(
                "Batch %s delivery failed (status=%d, error=%s). Reverted to pending. Next retry in %.1fs.",
                batch_id,
                result.status_code,
                result.error_detail,
                delay,
            )
            if self.on_status_change:
                self.on_status_change("sync_error", f"Sync failed: {result.error_detail or result.status_code}")
            return False
