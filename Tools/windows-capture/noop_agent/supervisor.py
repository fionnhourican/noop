"""Supervisor managing background BLE connection, queue, sync worker, and tray UI."""

import asyncio
import logging
import sys
import threading
from typing import Optional

from noop_agent.config import AgentConfig
from noop_agent.storage.local_db import LocalDatabase
from noop_agent.storage.queue import DurableQueue
from noop_agent.tray.application import TrayApp

logger = logging.getLogger(__name__)

MUTEX_NAME = "Global\\NOOP_HomeLab_Collector_Mutex"


class SingleInstance:
    """Enforce single-instance execution via Windows Named Mutex or file lock."""

    def __init__(self, mutex_name: str = MUTEX_NAME):
        self.mutex_name = mutex_name
        self.handle = None
        self.lock_file = None

    def acquire(self) -> bool:
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.windll.kernel32
                ERROR_ALREADY_EXISTS = 183

                self.handle = kernel32.CreateMutexW(None, wintypes.BOOL(False), self.mutex_name)
                last_error = kernel32.GetLastError()
                if last_error == ERROR_ALREADY_EXISTS:
                    logger.error("Another instance of NOOP Collector is already running.")
                    return False
                return True
            except Exception as e:
                logger.warning("Windows mutex creation failed (%s), using file lock.", e)

        # Cross-platform fallback lock file
        import tempfile
        lock_path = Path(tempfile.gettempdir()) / "noop_collector.lock"
        try:
            self.lock_file = open(lock_path, "w")
            if sys.platform != "win32":
                import fcntl
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except Exception:
            logger.error("Another instance of NOOP Collector is active (file lock held).")
            return False

    def release(self) -> None:
        if sys.platform == "win32" and self.handle:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self.handle)
                self.handle = None
            except Exception:
                pass
        if self.lock_file:
            try:
                self.lock_file.close()
                self.lock_file = None
            except Exception:
                pass


class AgentSupervisor:
    """Master supervisor coordinating all agent subsystems."""

    def __init__(self, config: AgentConfig, enable_tray: bool = True):
        self.config = config
        self.enable_tray = enable_tray
        self.single_instance = SingleInstance()

        self.db = LocalDatabase(self.config.db_path)
        self.queue = DurableQueue(self.db)
        self.tray_app: Optional[TrayApp] = None
        self.tray_thread: Optional[threading.Thread] = None

        self.stop_event = asyncio.Event()
        self.is_running = False

    def _setup_tray(self) -> None:
        if not self.enable_tray:
            return

        def on_exit():
            logger.info("Tray requested exit; stopping supervisor.")
            self.stop_event.set()

        def on_sync():
            logger.info("Manual sync requested from system tray.")

        self.tray_app = TrayApp(
            on_sync_now=on_sync,
            on_exit=on_exit,
            config_path=str(self.config.data_dir / "config.yaml"),
            log_path=str(self.config.log_path),
        )

        self.tray_thread = threading.Thread(
            target=self.tray_app.run,
            name="NOOP_TrayThread",
            daemon=True,
        )
        self.tray_thread.start()
        self.tray_app.update_state("disconnected", "Ready")

    def update_status(self, state: str, detail: Optional[str] = None) -> None:
        """Propagate state change to system tray UI."""
        if self.tray_app:
            self.tray_app.update_state(state, detail)

    async def _health_monitor_loop(self) -> None:
        """Periodic heartbeat logging queue depth and status."""
        while not self.stop_event.is_set():
            try:
                stats = self.queue.get_stats()
                logger.info(
                    "Heartbeat: pending=%d in_flight=%d synced=%d",
                    stats["pending"],
                    stats["in_flight"],
                    stats["synced"],
                )
            except Exception as e:
                logger.error("Health monitor error: %s", e)

            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                pass

    async def start(self) -> None:
        """Start the supervisor and all child subsystems."""
        if not self.single_instance.acquire():
            logger.error("Exiting: single-instance mutex could not be acquired.")
            sys.exit(1)

        logger.info("Starting NOOP Windows Collector Agent (db=%s)", self.config.db_path)

        # 1. Recover any unconfirmed in-flight batches from previous run
        recovered = self.queue.recover_in_flight()
        if recovered > 0:
            logger.info("Recovered %d orphaned in-flight records back to pending.", recovered)

        # 2. Start tray UI thread
        self._setup_tray()
        self.is_running = True

        # 3. Start health monitor loop
        monitor_task = asyncio.create_task(self._health_monitor_loop())

        # Wait until termination event
        await self.stop_event.wait()
        logger.info("Shutdown signal received.")

        # Cleanup
        monitor_task.cancel()
        await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully terminate subsystems and flush database."""
        if not self.is_running:
            return
        self.is_running = False
        logger.info("Shutting down supervisor subsystems...")

        if self.tray_app:
            self.tray_app.stop()

        self.db.close()
        self.single_instance.release()
        logger.info("Shutdown complete.")
