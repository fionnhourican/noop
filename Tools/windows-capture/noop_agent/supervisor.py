"""Supervisor managing independent collector subsystems, BLE transport, and durable persistence."""

import asyncio
import ctypes
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Optional

from noop_agent.ble.whoop4 import Whoop4Device
from noop_agent.config import AgentConfig
from noop_agent.protocol.models import ObservationProvenance
from noop_agent.storage.local_db import LocalDatabase
from noop_agent.storage.queue import DurableQueue
from noop_agent.tray.application import TrayApp

logger = logging.getLogger(__name__)

MUTEX_NAME = "Global\\NOOP_HomeLab_Collector_Mutex"


class SingleInstanceLock:
    """Enforces single-instance execution via Windows Named Mutex or file lock fallback."""

    def __init__(self, lock_file_path: Path):
        self.lock_file_path = lock_file_path
        self.mutex_handle = None
        self.file_handle = None

    def acquire(self) -> bool:
        if sys.platform == "win32":
            try:
                kernel32 = ctypes.windll.kernel32
                mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
                last_error = kernel32.GetLastError()
                ERROR_ALREADY_EXISTS = 183
                if last_error == ERROR_ALREADY_EXISTS:
                    if mutex:
                        kernel32.CloseHandle(mutex)
                    return False
                self.mutex_handle = mutex
                return True
            except Exception as e:
                logger.warning("Windows mutex acquisition failed (%s); falling back to file lock", e)

        # Fallback file lock
        try:
            self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_handle = open(self.lock_file_path, "w")
            if sys.platform != "win32":
                import fcntl
                fcntl.flock(self.file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.file_handle.write(str(os.getpid()))
            self.file_handle.flush()
            return True
        except Exception:
            return False

    def release(self) -> None:
        if self.mutex_handle and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.CloseHandle(self.mutex_handle)
                self.mutex_handle = None
            except Exception:
                pass

        if self.file_handle:
            try:
                self.file_handle.close()
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
            except Exception:
                pass


class AgentSupervisor:
    """Central supervisor coordinating storage, BLE collection, tray UI, and sync."""

    def __init__(self, config: AgentConfig, enable_tray: bool = True):
        self.config = config
        self.enable_tray = enable_tray
        self.stop_event = asyncio.Event()

        # Single instance lock
        self.lock = SingleInstanceLock(config.data_dir / "agent.lock")

        # Storage subsystem
        self.db = LocalDatabase(config.db_path)
        self.queue = DurableQueue(self.db)

        # Tray subsystem
        self.tray: Optional[TrayApp] = None
        self.tray_thread: Optional[threading.Thread] = None

        # Bounded Live Pipeline queue (Engineering Review Addendum B)
        self.live_queue: asyncio.Queue[ObservationProvenance] = asyncio.Queue(maxsize=1000)

        # BLE Subsystem
        self.device = Whoop4Device(
            target_address=config.device.address,
            scan_timeout=config.ble.scan_timeout,
            auto_pair=config.ble.auto_pair,
            on_record=self._on_live_record_received,
            on_raw_frame=self._on_raw_frame_received,
            on_state_change=self.set_state,
        )

        # State telemetry
        self.current_state = "starting"
        self.is_paused = False
        self.last_sync_time: Optional[float] = None
        self.latest_hr: Optional[int] = None
        self.latest_battery: Optional[float] = None

    def _on_tray_sync_now(self) -> None:
        logger.info("Manual sync triggered from system tray.")

    def _on_tray_toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        logger.info("Collection %s from tray.", "paused" if self.is_paused else "resumed")
        if self.is_paused:
            asyncio.create_task(self.device.stop())

    def _on_tray_exit(self) -> None:
        logger.info("Shutdown requested from system tray.")
        self.stop_event.set()

    def set_state(self, state: str, detail: Optional[str] = None) -> None:
        """Update system state and propagate to tray UI."""
        self.current_state = state
        if self.tray:
            self.tray.update_state(state, detail)

    def _on_raw_frame_received(self, device_id: str, frame_bytes: bytes, char_uuid: str) -> Optional[int]:
        """Save raw frame immutably in local database."""
        inner_type = frame_bytes[4] if len(frame_bytes) > 4 else None
        return self.queue.enqueue_raw_frame(
            device_id=device_id,
            frame_bytes=frame_bytes,
            char_uuid=char_uuid,
            inner_type=inner_type,
        )

    def _on_live_record_received(self, record: ObservationProvenance) -> None:
        """Thread-safe enqueue into bounded live pipeline with explicit backpressure."""
        try:
            self.live_queue.put_nowait(record)
        except asyncio.QueueFull:
            logger.warning("Live pipeline queue full (1000 records). Dropping oldest to relieve backpressure.")
            try:
                self.live_queue.get_nowait()
                self.live_queue.put_nowait(record)
            except Exception:
                pass

    async def _live_pipeline_worker(self) -> None:
        """Worker consuming live records and persisting to SQLite."""
        while not self.stop_event.is_set():
            try:
                record = await asyncio.wait_for(self.live_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            try:
                # Update status telemetry
                if record.record_type == "heart_rate" and isinstance(record.value, int):
                    self.latest_hr = record.value
                    detail = f"{self.latest_hr} bpm"
                    if self.latest_battery is not None:
                        detail += f" ({self.latest_battery:.0f}%)"
                    self.set_state("connected", detail)
                elif record.record_type == "battery" and isinstance(record.value, dict):
                    soc = record.value.get("soc_percent")
                    if soc is not None:
                        self.latest_battery = float(soc)

                # Commit observation to durable queue
                self.queue.enqueue_record(
                    device_id=record.device_id,
                    record_type=record.record_type,
                    timestamp=record.timestamp_utc,
                    value=record.value,
                    unit=record.unit,
                    data_origin=record.data_origin,
                    validation_status=record.validation_status,
                    protocol_version=record.protocol_version,
                    decoder_version=record.decoder_version,
                    raw_frame_id=record.raw_frame_id,
                    metadata=record.metadata,
                    timestamp_utc=record.timestamp_utc,
                    reception_utc=record.reception_utc,
                )
            except Exception as e:
                logger.error("Failed to commit live record to SQLite: %s", e)
            finally:
                self.live_queue.task_done()

    async def _ble_lifecycle_supervisor(self) -> None:
        """Supervisor loop managing connection retries, backoff, and reconnection."""
        retry_delay = self.config.ble.min_retry_delay

        while not self.stop_event.is_set():
            if self.is_paused:
                await asyncio.sleep(1.0)
                continue

            try:
                logger.info("Attempting WHOOP BLE connection...")
                success = await self.device.connect_and_stream()
                if success:
                    retry_delay = self.config.ble.min_retry_delay
                    # Wait while connection remains active
                    while self.device.conn.is_connected and not self.stop_event.is_set() and not self.is_paused:
                        await asyncio.sleep(1.0)
                else:
                    logger.info("Connection attempt unfulfilled. Retrying in %.1fs...", retry_delay)
            except Exception as e:
                logger.warning("BLE supervisor exception: %s. Retrying in %.1fs...", e, retry_delay)

            if not self.stop_event.is_set() and not self.is_paused:
                await asyncio.sleep(retry_delay)
                # Exponential backoff with ceiling
                retry_delay = min(retry_delay * 1.5, self.config.ble.max_retry_delay)

    async def _health_monitor_loop(self) -> None:
        """Periodic background monitor checking subsystem health."""
        while not self.stop_event.is_set():
            try:
                stats = self.queue.get_stats()
                logger.debug(
                    "Queue health: pending=%d, in_flight=%d, synced=%d, live_q=%d",
                    stats["pending"],
                    stats["in_flight"],
                    stats["synced"],
                    self.live_queue.qsize(),
                )
            except Exception as e:
                logger.error("Health monitor exception: %s", e)
            await asyncio.sleep(10.0)

    async def start(self) -> None:
        """Start supervisor and all managed subsystems."""
        if not self.lock.acquire():
            logger.error("Another instance of NOOP Collector is already running. Exiting.")
            sys.exit(1)

        logger.info("Starting NOOP Agent Supervisor (PID %d)", os.getpid())
        logger.info("Database: %s", self.config.db_path)

        # Recover any orphaned in-flight records from previous run
        recovered = self.queue.recover_in_flight()
        if recovered > 0:
            logger.info("Recovered %d in-flight record(s) back to pending queue.", recovered)

        # Initialize and launch system tray in separate thread
        if self.enable_tray:
            self.tray = TrayApp(
                on_sync_now=self._on_tray_sync_now,
                on_toggle_pause=self._on_tray_toggle_pause,
                on_exit=self._on_tray_exit,
                config_path=str(self.config.data_dir / "config.yaml"),
                log_path=str(self.config.log_path),
            )
            self.tray_thread = threading.Thread(target=self.tray.run, daemon=True)
            self.tray_thread.start()

        self.set_state("scanning")

        # Launch background tasks
        live_worker_task = asyncio.create_task(self._live_pipeline_worker())
        ble_task = asyncio.create_task(self._ble_lifecycle_supervisor())
        monitor_task = asyncio.create_task(self._health_monitor_loop())

        try:
            await self.stop_event.wait()
        finally:
            logger.info("Stopping supervisor tasks...")
            ble_task.cancel()
            live_worker_task.cancel()
            monitor_task.cancel()
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully terminate subsystems and flush queues."""
        logger.info("Shutting down NOOP Agent Supervisor...")
        self.set_state("offline")
        await self.device.stop()
        if self.tray:
            self.tray.stop()
        self.db.close()
        self.lock.release()
        logger.info("Shutdown complete.")
