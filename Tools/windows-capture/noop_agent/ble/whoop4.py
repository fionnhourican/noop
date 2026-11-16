"""WHOOP 4.0 device orchestrator and live stream manager."""

import asyncio
import logging
from typing import Any, Callable, Optional

from noop_agent.ble.characteristics import (
    CMD_GET_BATTERY_LEVEL,
    CMD_SEND_R10_R11_REALTIME,
    CMD_TOGGLE_REALTIME_HR,
    DEVINFO_FIRMWARE_REV_UUID,
    DEVINFO_HARDWARE_REV_UUID,
    DEVINFO_MODEL_NUMBER_UUID,
    DEVINFO_SERIAL_NUMBER_UUID,
    WHOOP4_CMD_WRITE_UUID,
)
from noop_agent.ble.connection import BleConnectionManager
from noop_agent.ble.framing import build_command_frame
from noop_agent.ble.notifications import NotificationDispatcher
from noop_agent.ble.scanner import WhoopScanner
from noop_agent.protocol.decoder import Whoop4Decoder
from noop_agent.protocol.models import DeviceInfo, ObservationProvenance

logger = logging.getLogger(__name__)


class Whoop4Device:
    """Manages the full connection, initialization, live streaming, and decoding loop for WHOOP 4.0."""

    def __init__(
        self,
        target_address: Optional[str] = None,
        scan_timeout: float = 10.0,
        auto_pair: bool = True,
        on_record: Optional[Callable[[ObservationProvenance], None]] = None,
        on_raw_frame: Optional[Callable[[str, bytes, str], Optional[int]]] = None,
        on_state_change: Optional[Callable[[str, Optional[str]], None]] = None,
    ):
        self.target_address = target_address
        self.scan_timeout = scan_timeout
        self.auto_pair = auto_pair

        self.on_record = on_record
        self.on_raw_frame = on_raw_frame
        self.on_state_change = on_state_change

        self.scanner = WhoopScanner(target_address, scan_timeout)
        self.conn = BleConnectionManager(
            on_disconnected=self._on_ble_disconnected,
            auto_pair=auto_pair,
        )
        self.dispatcher = NotificationDispatcher(
            on_frame=self._on_reassembled_frame,
            on_standard_hr=self._on_sig_hr,
            on_standard_battery=self._on_sig_battery,
        )
        self.decoder = Whoop4Decoder()

        self.device_info: Optional[DeviceInfo] = None
        self._seq = 1
        self._keepalive_task: Optional[asyncio.Task] = None
        self._is_collecting = False

    def _notify_state(self, state: str, detail: Optional[str] = None):
        if self.on_state_change:
            self.on_state_change(state, detail)

    def _next_seq(self) -> int:
        s = self._seq
        self._seq = (self._seq + 1) & 0xFF
        return s

    def _on_ble_disconnected(self, _client):
        self._is_collecting = False
        if self._keepalive_task:
            self._keepalive_task.cancel()
            self._keepalive_task = None
        self._notify_state("disconnected", "Link dropped")

    def _on_sig_hr(self, bpm: int, rr_list):
        """Handle standard Bluetooth SIG heart rate measurement."""
        device_id = self.device_info.address if self.device_info else "whoop4"
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)

        rec = ObservationProvenance(
            device_id=device_id,
            record_type="heart_rate",
            timestamp_utc=now,
            reception_utc=now,
            data_origin="live",
            validation_status="valid",
            value=bpm,
            unit="bpm",
            metadata={"source": "sig_2a37", "rr_intervals": rr_list},
        )
        if self.on_record:
            self.on_record(rec)

    def _on_sig_battery(self, level_pct: int):
        """Handle standard Bluetooth SIG battery level notification."""
        device_id = self.device_info.address if self.device_info else "whoop4"
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)

        rec = ObservationProvenance(
            device_id=device_id,
            record_type="battery",
            timestamp_utc=now,
            reception_utc=now,
            data_origin="live",
            validation_status="valid",
            value={"soc_percent": float(level_pct)},
            unit="percent",
            metadata={"source": "sig_2a19"},
        )
        if self.on_record:
            self.on_record(rec)

    def _on_reassembled_frame(self, char_uuid: str, frame_bytes: bytes):
        """Handle complete reassembled frame from proprietary WHOOP 4.0 notify channel."""
        device_id = self.device_info.address if self.device_info else "whoop4"

        # Persist raw frame reference if callback provided
        raw_frame_id = None
        if self.on_raw_frame:
            try:
                raw_frame_id = self.on_raw_frame(device_id, frame_bytes, char_uuid)
            except Exception as e:
                logger.error("Failed to persist raw frame: %s", e)

        # Decode frame into normalized records
        records = self.decoder.decode_frame(
            frame=frame_bytes,
            device_id=device_id,
            raw_frame_id=raw_frame_id,
        )

        for rec in records:
            if self.on_record:
                self.on_record(rec)

    async def _read_device_metadata(self, address: str, name: Optional[str]) -> DeviceInfo:
        """Read standard Device Information Service strings."""
        info = DeviceInfo(address=address, name=name)

        async def read_str(uuid: str) -> Optional[str]:
            raw = await self.conn.read_gatt_char(uuid)
            if raw:
                try:
                    return raw.decode("utf-8", errors="replace").strip("\x00 \t\r\n")
                except Exception:
                    return None
            return None

        info.model = await read_str(DEVINFO_MODEL_NUMBER_UUID) or "WHOOP 4.0"
        info.serial_number = await read_str(DEVINFO_SERIAL_NUMBER_UUID)
        info.firmware_version = await read_str(DEVINFO_FIRMWARE_REV_UUID)
        info.hardware_version = await read_str(DEVINFO_HARDWARE_REV_UUID)

        logger.info(
            "Device identified: model=%s, serial=%s, fw=%s, hw=%s",
            info.model,
            info.serial_number,
            info.firmware_version,
            info.hardware_version,
        )
        return info

    async def write_command(self, cmd: int, payload: bytes = b"\x00", response: bool = False) -> bool:
        """Build and send a framed WHOOP 4.0 command to the command write characteristic."""
        seq = self._next_seq()
        frame = build_command_frame(cmd, seq=seq, payload=payload)
        return await self.conn.write_gatt_char(WHOOP4_CMD_WRITE_UUID, frame, response=response)

    async def _arm_realtime_stream(self) -> None:
        """Activate the live HR + R-R interval stream."""
        logger.info("Arming realtime sensor stream (SEND_R10_R11_REALTIME + TOGGLE_REALTIME_HR)...")
        # 1. Arm R10/R11 realtime stream
        await self.write_command(CMD_SEND_R10_R11_REALTIME, payload=b"\x01", response=False)
        # 2. Toggle realtime heart rate streaming
        await self.write_command(CMD_TOGGLE_REALTIME_HR, payload=b"\x01", response=False)

    async def _keepalive_loop(self) -> None:
        """Periodically re-issue realtime arming commands to prevent link supervision timeout."""
        while self._is_collecting and self.conn.is_connected:
            await asyncio.sleep(15.0)
            if not self._is_collecting or not self.conn.is_connected:
                break
            try:
                await self._arm_realtime_stream()
            except Exception as e:
                logger.warning("Keepalive re-arm failed: %s", e)

    async def connect_and_stream(self) -> bool:
        """Find strap, connect, subscribe to notifications, and begin live collection."""
        self._notify_state("scanning", "Scanning for strap...")
        device: Optional[Any] = await self.scanner.find_device()
        if not device:
            self._notify_state("disconnected", "Strap not found")
            return False

        self._notify_state("connecting", f"Connecting to {device.address}...")
        ok = await self.conn.connect(device)
        if not ok or not self.conn.client:
            self._notify_state("error", "Connection failed")
            return False

        # Read metadata
        self.device_info = await self._read_device_metadata(device.address, device.name)

        # Subscribe notifications
        await self.dispatcher.subscribe_all(self.conn.client)

        # Benign handshake query: request battery level to confirm responsiveness & trigger bonding
        await self.write_command(CMD_GET_BATTERY_LEVEL, payload=b"\x00", response=False)
        await asyncio.sleep(0.5)

        # Arm realtime stream
        await self._arm_realtime_stream()

        self._is_collecting = True
        self._notify_state("connected", "Live stream active")

        # Start periodic keepalive re-arm
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        return True

    async def stop(self) -> None:
        """Stop streaming, cancel keepalive, and disconnect."""
        self._is_collecting = False
        if self._keepalive_task:
            self._keepalive_task.cancel()
            self._keepalive_task = None

        if self.conn.client:
            await self.dispatcher.unsubscribe_all(self.conn.client)
        await self.conn.disconnect()
        self._notify_state("disconnected", "Stopped")
