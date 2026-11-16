"""WHOOP 4.0 packet framing, checksum validation, stream reassembly, and standard SIG decoders."""

import struct
import zlib
from typing import List, Optional, Tuple

from noop_agent.ble.characteristics import (
    CMD_HISTORICAL_DATA_RESULT,
    META_HISTORY_COMPLETE,
    META_HISTORY_END,
    META_HISTORY_START,
    PACKET_COMMAND,
    PACKET_METADATA,
)

# Minimum bytes for a structurally valid WHOOP 4.0 frame:
# [0xAA] + [len u16 LE] + [crc8] + [type] + [seq] + [cmd] + [crc32 LE] = 1 + 2 + 1 + 3 + 4 = 11 bytes
WHOOP4_MIN_FRAME_BYTES = 11

# WHOOP 4.0 Metadata Offsets
WHOOP4_INNER_OFF = 4
WHOOP4_META_TYPE_OFF = 6
WHOOP4_META_TRIM_OFF = 17
WHOOP4_END_DATA_LEN = 8


def _crc8_table() -> List[int]:
    """Generate CRC-8 lookup table (polynomial 0x07, unreflected)."""
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if (c & 0x80) else (c << 1) & 0xFF
        table.append(c)
    return table


_CRC8_TABLE = _crc8_table()


def crc8(data: bytes) -> int:
    """CRC-8 (poly 0x07, init 0x00) over the two length bytes of the WHOOP 4.0 header."""
    crc = 0
    for b in data:
        crc = _CRC8_TABLE[crc ^ b]
    return crc


def crc32(data: bytes) -> int:
    """Standard zlib reflected CRC-32 (poly 0xEDB88320) over the inner payload."""
    return zlib.crc32(data) & 0xFFFFFFFF


def build_command_frame(cmd: int, seq: int = 0, payload: bytes = b"\x00") -> bytes:
    """Construct a complete, wire-ready WHOOP 4.0 COMMAND frame.

    Envelope:
      [0xAA][len u16 LE][crc8][type=35][seq][cmd][payload...][crc32 LE]
    """
    inner = bytes([PACKET_COMMAND, seq & 0xFF, cmd & 0xFF]) + payload
    length = (3 + len(payload)) + 4  # inner (type+seq+cmd+payload) + 4-byte CRC32 trailer
    len_bytes = bytes([length & 0xFF, (length >> 8) & 0xFF])
    header_crc = crc8(len_bytes)
    trailer = crc32(inner)
    trailer_bytes = struct.pack("<I", trailer)
    return bytes([0xAA]) + len_bytes + bytes([header_crc]) + inner + trailer_bytes


def verify_whoop4_frame(frame: bytes) -> bool:
    """Validate full packet integrity: SOF, minimum length, declared length, CRC-8 header, and CRC-32 trailer.

    CRC is the protocol's primary data integrity gate. Any frame failing validation must be rejected
    before parsing to avoid corrupting analytics or advancing trim cursors.
    """
    if len(frame) < WHOOP4_MIN_FRAME_BYTES:
        return False
    if frame[0] != 0xAA:
        return False

    declared = frame[1] | (frame[2] << 8)
    total = declared + 4
    if total != len(frame):
        return False

    if crc8(bytes(frame[1:3])) != frame[3]:
        return False

    inner = bytes(frame[4:total - 4])
    wire_crc = struct.unpack_from("<I", frame, total - 4)[0]
    return crc32(inner) == wire_crc


def history_end_data_whoop4(frame: bytes) -> Optional[bytes]:
    """If `frame` is a CRC-valid WHOOP 4.0 METADATA HISTORY_END, return its 8-byte end_data

    (trim u32 + next u32 at frame[17:25]) to echo back in the trim acknowledgment.
    """
    if len(frame) < WHOOP4_META_TRIM_OFF + WHOOP4_END_DATA_LEN:
        return None
    if frame[WHOOP4_INNER_OFF] != PACKET_METADATA:
        return None
    if frame[WHOOP4_META_TYPE_OFF] != META_HISTORY_END:
        return None
    if not verify_whoop4_frame(frame):
        return None
    return bytes(frame[WHOOP4_META_TRIM_OFF:WHOOP4_META_TRIM_OFF + WHOOP4_END_DATA_LEN])


def build_history_ack_whoop4(end_data: bytes, seq: int = 0) -> bytes:
    """Build the WHOOP 4.0 HISTORICAL_DATA_RESULT(23) ack: payload = 0x01 + 8-byte end_data."""
    return build_command_frame(
        CMD_HISTORICAL_DATA_RESULT,
        seq=seq,
        payload=b"\x01" + bytes(end_data),
    )


def is_metadata_frame(frame: bytes, expected_meta_type: Optional[int] = None) -> bool:
    """Check if a frame is a valid METADATA frame matching the optional meta_type."""
    if len(frame) < 7 or frame[0] != 0xAA or frame[WHOOP4_INNER_OFF] != PACKET_METADATA:
        return False
    if expected_meta_type is not None and frame[WHOOP4_META_TYPE_OFF] != expected_meta_type:
        return False
    return verify_whoop4_frame(frame)


class Reassembler:
    """Stream reassembler for segmented BLE notifications.

    Maintains an independent byte buffer per notify characteristic to prevent cross-channel interleaving.
    Accumulates incoming fragments, synchronizes to 0xAA (SOF), enforces length sanity bounds,
    and extracts complete frames.
    """

    def __init__(self):
        self.buf = bytearray()

    def _total_len(self) -> Optional[int]:
        """Compute expected total on-wire length from the buffer header."""
        if len(self.buf) < 3:
            return None
        declared = self.buf[1] | (self.buf[2] << 8)
        return declared + 4

    def feed(self, data: bytes) -> List[bytes]:
        """Feed newly received notification bytes and return all newly completed frames."""
        self.buf.extend(data)
        out: List[bytes] = []

        while True:
            # Synchronize to next Start-Of-Frame (0xAA)
            sof = self.buf.find(0xAA)
            if sof == -1:
                self.buf.clear()
                break
            if sof > 0:
                del self.buf[:sof]

            total = self._total_len()
            if total is None:
                break

            # Guard against absurd length from corrupted SOF before waiting for more bytes
            if total <= 0 or total > 4096:
                del self.buf[:1]
                continue

            if len(self.buf) < total:
                # Need more bytes from subsequent notifications
                break

            out.append(bytes(self.buf[:total]))
            del self.buf[:total]

        return out

    def reset(self) -> None:
        """Clear reassembly buffer upon disconnection or error."""
        self.buf.clear()


def parse_standard_hr(data: bytes) -> Tuple[Optional[int], List[int]]:
    """Parse standard Bluetooth SIG Heart Rate Measurement (0x2A37).

    Returns:
        (heart_rate_bpm, rr_intervals_ms)
    """
    if not data or len(data) < 2:
        return None, []

    flags = data[0]
    hr_is_u16 = bool(flags & 0x01)
    ee_present = bool(flags & 0x08)
    rr_present = bool(flags & 0x10)

    offset = 1
    if hr_is_u16:
        if len(data) < 3:
            return None, []
        bpm = data[1] | (data[2] << 8)
        offset += 2
    else:
        bpm = data[1]
        offset += 1

    if ee_present:
        offset += 2  # Energy Expended (u16 LE)

    rr_intervals: List[int] = []
    if rr_present:
        while offset + 2 <= len(data):
            # Unit: 1/1024 second -> convert to milliseconds
            raw_rr = data[offset] | (data[offset + 1] << 8)
            rr_ms = int(round(raw_rr * 1000.0 / 1024.0))
            if rr_ms > 0:
                rr_intervals.append(rr_ms)
            offset += 2

    return bpm, rr_intervals


def parse_standard_battery(data: bytes) -> Optional[int]:
    """Parse standard Bluetooth SIG Battery Level (0x2A19)."""
    if not data:
        return None
    val = data[0]
    return val if 0 <= val <= 100 else None
