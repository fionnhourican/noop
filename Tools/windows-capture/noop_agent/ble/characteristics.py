"""WHOOP 4.0 and standard BLE GATT service and characteristic UUID definitions."""

# ==============================================================================
# WHOOP 4.0 Proprietary GATT Service & Characteristics
# ==============================================================================
WHOOP4_SERVICE_UUID = "61080001-8d6d-82b8-614a-1c8cb0f8dcc6"
WHOOP4_CMD_WRITE_UUID = "61080002-8d6d-82b8-614a-1c8cb0f8dcc6"
WHOOP4_NOTIFY_0_UUID = "61080003-8d6d-82b8-614a-1c8cb0f8dcc6"
WHOOP4_NOTIFY_1_UUID = "61080004-8d6d-82b8-614a-1c8cb0f8dcc6"
WHOOP4_NOTIFY_2_UUID = "61080005-8d6d-82b8-614a-1c8cb0f8dcc6"

WHOOP4_NOTIFY_UUIDS = [
    WHOOP4_NOTIFY_0_UUID,
    WHOOP4_NOTIFY_1_UUID,
    WHOOP4_NOTIFY_2_UUID,
]

# ==============================================================================
# Standard Bluetooth SIG Services & Characteristics
# ==============================================================================
# Heart Rate Service
HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# Battery Service
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

# Device Information Service
DEVINFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
DEVINFO_MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
DEVINFO_SERIAL_NUMBER_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
DEVINFO_FIRMWARE_REV_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
DEVINFO_HARDWARE_REV_UUID = "00002a27-0000-1000-8000-00805f9b34fb"

# ==============================================================================
# WHOOP 4.0 Packet Types (Inner wire byte at offset 4)
# ==============================================================================
PACKET_COMMAND = 35
PACKET_COMMAND_RESPONSE = 36
PACKET_REALTIME_DATA = 40
PACKET_REALTIME_RAW_DATA = 43
PACKET_HISTORICAL_DATA = 47
PACKET_EVENT = 48
PACKET_METADATA = 49
PACKET_CONSOLE_LOGS = 50

# Metadata sub-types
META_HISTORY_START = 1
META_HISTORY_END = 2
META_HISTORY_COMPLETE = 3

# Event sub-types
EVENT_BATTERY_LEVEL = 26
EVENT_EXTENDED_BATTERY = 98

# ==============================================================================
# WHOOP 4.0 Command Identifiers (Reversible / Non-destructive)
# ==============================================================================
CMD_REPORT_VERSION_INFO = 7
CMD_SET_CLOCK = 10
CMD_GET_CLOCK = 11
CMD_TOGGLE_REALTIME_HR = 3          # In whoop_sync: activates realtime streaming
CMD_SEND_HISTORICAL_DATA = 22       # In whoop_sync: requests historical chunks
CMD_HISTORICAL_DATA_RESULT = 23     # In whoop_sync: trim acknowledgment
CMD_GET_BATTERY_LEVEL = 26          # Benign command eliciting response + bonding
CMD_GET_DATA_RANGE = 34
CMD_GET_HELLO_HARVARD = 35
CMD_SEND_R10_R11_REALTIME = 63      # Arms realtime stream alongside toggle
WHOOP4_RUN_HAPTICS_PATTERN = 79     # Haptic buzz for find-my-strap
