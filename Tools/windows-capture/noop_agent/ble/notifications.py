"""GATT notification subscriptions and per-channel frame reassembly dispatch."""

import logging
from typing import Any, Callable, Dict, List, Optional

from noop_agent.ble.characteristics import (
    BATTERY_LEVEL_UUID,
    HR_MEASUREMENT_UUID,
    WHOOP4_NOTIFY_UUIDS,
)
from noop_agent.ble.framing import (
    Reassembler,
    parse_standard_battery,
    parse_standard_hr,
)

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Subscribes to BLE notifications and handles per-channel stream reassembly."""

    def __init__(
        self,
        on_frame: Optional[Callable[[str, bytes], None]] = None,
        on_standard_hr: Optional[Callable[[int, List[int]], None]] = None,
        on_standard_battery: Optional[Callable[[int], None]] = None,
    ):
        self.on_frame = on_frame
        self.on_standard_hr = on_standard_hr
        self.on_standard_battery = on_standard_battery

        # Dedicated reassembler per proprietary notify characteristic to avoid interleaving
        self.reassemblers: Dict[str, Reassembler] = {
            uuid.lower(): Reassembler() for uuid in WHOOP4_NOTIFY_UUIDS
        }
        self.subscribed_uuids: List[str] = []

    def _handle_standard_hr(self, _sender, data: bytearray):
        bpm, rr_list = parse_standard_hr(bytes(data))
        if bpm is not None:
            logger.debug("Live Standard HR: %d bpm, R-R count=%d", bpm, len(rr_list))
            if self.on_standard_hr:
                self.on_standard_hr(bpm, rr_list)

    def _handle_standard_battery(self, _sender, data: bytearray):
        level = parse_standard_battery(bytes(data))
        if level is not None:
            logger.info("Standard Battery Level: %d%%", level)
            if self.on_standard_battery:
                self.on_standard_battery(level)

    def _make_channel_handler(self, char_uuid: str):
        u_lower = char_uuid.lower()
        reassembler = self.reassemblers.get(u_lower)

        def handler(_sender, data: bytearray):
            if not reassembler:
                return
            frames = reassembler.feed(bytes(data))
            for frame in frames:
                if self.on_frame:
                    self.on_frame(char_uuid, frame)

        return handler

    async def subscribe_all(self, client: Any) -> None:
        """Subscribe to all standard and proprietary notification characteristics."""
        self.subscribed_uuids.clear()
        for reassembler in self.reassemblers.values():
            reassembler.reset()

        # 1. Standard Heart Rate (works unbonded)
        try:
            await client.start_notify(HR_MEASUREMENT_UUID, self._handle_standard_hr)
            self.subscribed_uuids.append(HR_MEASUREMENT_UUID)
            logger.info("Subscribed to Standard Heart Rate (%s)", HR_MEASUREMENT_UUID)
        except Exception as e:
            logger.warning("Could not subscribe to standard HR (%s): %s", HR_MEASUREMENT_UUID, e)

        # 2. Standard Battery Service
        try:
            await client.start_notify(BATTERY_LEVEL_UUID, self._handle_standard_battery)
            self.subscribed_uuids.append(BATTERY_LEVEL_UUID)
            logger.info("Subscribed to Standard Battery Level (%s)", BATTERY_LEVEL_UUID)
        except Exception as e:
            logger.debug("Standard battery subscribe skipped/failed: %s", e)

        # 3. WHOOP 4.0 Proprietary Notify Channels (0, 1, 2)
        for char_uuid in WHOOP4_NOTIFY_UUIDS:
            try:
                handler = self._make_channel_handler(char_uuid)
                await client.start_notify(char_uuid, handler)
                self.subscribed_uuids.append(char_uuid)
                logger.info("Subscribed to WHOOP 4 notify channel (%s)", char_uuid)
            except Exception as e:
                logger.warning("Could not subscribe to WHOOP channel (%s): %s", char_uuid, e)

    async def unsubscribe_all(self, client: Any) -> None:
        """Stop all active notification subscriptions."""
        for char_uuid in list(self.subscribed_uuids):
            try:
                await client.stop_notify(char_uuid)
            except Exception:
                pass
        self.subscribed_uuids.clear()
        for reassembler in self.reassemblers.values():
            reassembler.reset()
