"""Single BLE connection manager with WinRT pairing handling and lifecycle management."""

import asyncio
import logging
import sys
from typing import TYPE_CHECKING, Any, Callable, Optional

from noop_agent.ble.characteristics import WHOOP4_SERVICE_UUID

if TYPE_CHECKING:
    from bleak import BleakClient
    from bleak.backends.device import BLEDevice
else:
    BleakClient = Any
    BLEDevice = Any

logger = logging.getLogger(__name__)


class BleConnectionManager:
    """Manages the lifecycle of a single BLE connection to a WHOOP 4.0 strap."""

    def __init__(
        self,
        on_disconnected: Optional[Callable[[Any], None]] = None,
        auto_pair: bool = True,
    ):
        self.on_disconnected = on_disconnected
        self.auto_pair = auto_pair
        self.client: Optional[Any] = None
        self._lock = asyncio.Lock()
        self.is_connected = False
        self.device: Optional[Any] = None

    def _handle_disconnect(self, client: Any):
        logger.warning("BLE link disconnected: %s", getattr(client, "address", "unknown"))
        self.is_connected = False
        if self.on_disconnected:
            self.on_disconnected(client)

    async def connect(self, device: Any) -> bool:
        """Establish BLE connection, verify GATT services, and handle Windows pairing."""
        from bleak import BleakClient

        async with self._lock:
            # Enforce single connection ownership
            if self.client and self.client.is_connected:
                logger.warning("Existing BLE connection already open; closing it first.")
                await self.disconnect()

            self.device = device
            logger.info("Connecting to %s (%s)...", getattr(device, "name", "Strap") or "Strap", getattr(device, "address", ""))

            self.client = BleakClient(
                device,
                disconnected_callback=self._handle_disconnect,
            )

            try:
                await self.client.connect(timeout=20.0)
            except Exception as e:
                logger.error("BLE connection failed: %s", e)
                self.client = None
                return False

            if not self.client.is_connected:
                logger.error("Bleak reports client is not connected.")
                return False

            # Verify GATT service presence (Engineering Review Addendum A.5)
            services = [s.uuid.lower() for s in self.client.services]
            if WHOOP4_SERVICE_UUID.lower() not in services:
                logger.error(
                    "Connected device does not provide WHOOP 4 primary service (%s). Found: %s",
                    WHOOP4_SERVICE_UUID,
                    services,
                )
                await self.disconnect()
                return False

            # Windows WinRT pairing handling (Engineering Review Addendum A.6)
            if sys.platform == "win32" and self.auto_pair:
                try:
                    if hasattr(self.client, "pair"):
                        logger.info("Checking/requesting Windows OS-level pairing...")
                        paired = await self.client.pair()
                        logger.info("Windows pairing result: %s", paired)
                except Exception as e:
                    logger.warning("Pairing request returned: %s (continuing with connection)", e)

            # Try to acquire/negotiate optimal ATT MTU if supported
            try:
                if hasattr(self.client, "mtu_size"):
                    logger.info("ATT MTU size: %s", self.client.mtu_size)
            except Exception:
                pass

            self.is_connected = True
            logger.info("Successfully established BLE link to %s", getattr(device, "address", ""))
            return True

    async def disconnect(self) -> None:
        """Gracefully terminate BLE connection and release client."""
        if self.client:
            try:
                if self.client.is_connected:
                    await self.client.disconnect()
            except Exception as e:
                logger.debug("Error during BLE disconnect: %s", e)
            finally:
                self.client = None
                self.is_connected = False
                logger.info("BLE link cleanly closed.")

    async def write_gatt_char(
        self,
        char_uuid: str,
        data: bytes,
        response: bool = False,
    ) -> bool:
        """Write bytes to a GATT characteristic on the active connection."""
        if not self.client or not self.client.is_connected:
            logger.warning("Cannot write to GATT: client is not connected.")
            return False

        try:
            await self.client.write_gatt_char(char_uuid, data, response=response)
            return True
        except Exception as e:
            logger.error("GATT write failed for %s: %s", char_uuid, e)
            return False

    async def read_gatt_char(self, char_uuid: str) -> Optional[bytes]:
        """Read bytes from a GATT characteristic."""
        if not self.client or not self.client.is_connected:
            return None
        try:
            return await self.client.read_gatt_char(char_uuid)
        except Exception as e:
            logger.debug("GATT read failed for %s: %s", char_uuid, e)
            return None
