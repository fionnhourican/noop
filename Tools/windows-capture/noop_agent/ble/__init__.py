"""BLE transport and protocol package exports."""

from noop_agent.ble.characteristics import (
    HR_MEASUREMENT_UUID,
    WHOOP4_CMD_WRITE_UUID,
    WHOOP4_NOTIFY_UUIDS,
    WHOOP4_SERVICE_UUID,
)
from noop_agent.ble.framing import (
    Reassembler,
    build_command_frame,
    crc8,
    crc32,
    parse_standard_battery,
    parse_standard_hr,
    verify_whoop4_frame,
)

__all__ = [
    "WHOOP4_SERVICE_UUID",
    "WHOOP4_CMD_WRITE_UUID",
    "WHOOP4_NOTIFY_UUIDS",
    "HR_MEASUREMENT_UUID",
    "Reassembler",
    "crc8",
    "crc32",
    "build_command_frame",
    "verify_whoop4_frame",
    "parse_standard_hr",
    "parse_standard_battery",
]
