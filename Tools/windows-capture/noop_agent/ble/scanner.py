"""Bluetooth Low Energy scanner for WHOOP 4.0 straps."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, List, Optional

from noop_agent.ble.characteristics import WHOOP4_SERVICE_UUID

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
else:
    BLEDevice = Any

logger = logging.getLogger(__name__)


class WhoopScanner:
    """Discovers WHOOP 4.0 devices using service UUID filtering and heuristic name matching."""

    def __init__(self, target_address: Optional[str] = None, scan_timeout: float = 10.0):
        self.target_address = target_address.upper() if target_address else None
        self.scan_timeout = scan_timeout

    async def find_device(self) -> Optional[Any]:
        """Scan and locate the target or nearest advertising WHOOP 4.0 strap."""
        from bleak import BleakScanner

        logger.info(
            "Starting BLE scan (timeout=%.1fs, target=%s)...",
            self.scan_timeout,
            self.target_address or "ANY WHOOP 4.0",
        )

        found_devices: List[Any] = []

        def detection_callback(device: Any, adv_data: Any):
            # 1. Exact MAC address match
            if self.target_address and device.address.upper() == self.target_address:
                found_devices.append(device)
                return

            # 2. Service UUID match
            service_uuids = getattr(adv_data, "service_uuids", [])
            if WHOOP4_SERVICE_UUID.lower() in [u.lower() for u in service_uuids]:
                found_devices.append(device)
                return

            # 3. Heuristic name match (Engineering Review Addendum A.5)
            name = (getattr(device, "name", None) or getattr(adv_data, "local_name", None) or "").upper()
            if any(name.startswith(prefix) for prefix in ("WHOOP", "WHOOP 4", "WHOOP-4")):
                found_devices.append(device)

        scanner = BleakScanner(detection_callback=detection_callback)
        try:
            await scanner.start()
            elapsed = 0.0
            check_interval = 0.5
            while elapsed < self.scan_timeout:
                if found_devices:
                    if self.target_address:
                        break
                    elif len(found_devices) > 0 and elapsed >= 2.0:
                        break
                await asyncio.sleep(check_interval)
                elapsed += check_interval
        finally:
            try:
                await scanner.stop()
            except Exception:
                pass

        if not found_devices:
            logger.warning("No advertising WHOOP strap was discovered during scan.")
            return None

        selected = found_devices[0]
        logger.info("Found WHOOP strap: %s (%s)", getattr(selected, "name", "Unknown"), getattr(selected, "address", ""))
        return selected
