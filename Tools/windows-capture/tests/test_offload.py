"""Unit tests for WHOOP 4.0 historical offload framing, trim ACK, and persist-before-ack."""

import asyncio
import struct
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from noop_agent.ble.characteristics import (
    CMD_HISTORICAL_DATA_RESULT,
    META_HISTORY_COMPLETE,
    META_HISTORY_END,
    META_HISTORY_START,
    PACKET_COMMAND,
    PACKET_HISTORICAL_DATA,
    PACKET_METADATA,
)
from noop_agent.ble.framing import (
    build_history_ack_whoop4,
    crc8,
    crc32,
    history_end_data_whoop4,
    is_metadata_frame,
    verify_whoop4_frame,
)
from noop_agent.ble.whoop4 import Whoop4Device
from noop_agent.protocol.models import ObservationProvenance


def make_metadata_frame(meta_type: int, payload: bytes = b"", seq: int = 0) -> bytes:
    """Helper to synthesize a CRC-valid WHOOP 4.0 metadata frame."""
    inner = bytearray([PACKET_METADATA, seq, meta_type]) + payload
    inner_crc = crc32(inner)
    inner_with_crc = bytes(inner) + struct.pack("<I", inner_crc)

    length = len(inner_with_crc)
    len_bytes = struct.pack("<H", length)
    header_crc8 = crc8(len_bytes)

    return bytes([0xAA]) + len_bytes + bytes([header_crc8]) + inner_with_crc


class TestHistoricalOffload(unittest.TestCase):
    """Test suite for historical offload stream parsing and persist-before-ack guarantees."""

    def test_metadata_frame_detection(self):
        start_frame = make_metadata_frame(META_HISTORY_START)
        end_frame = make_metadata_frame(META_HISTORY_END, payload=b"\x00" * 20)
        comp_frame = make_metadata_frame(META_HISTORY_COMPLETE)

        self.assertTrue(verify_whoop4_frame(start_frame))
        self.assertTrue(verify_whoop4_frame(end_frame))
        self.assertTrue(verify_whoop4_frame(comp_frame))

        self.assertTrue(is_metadata_frame(start_frame, META_HISTORY_START))
        self.assertTrue(is_metadata_frame(end_frame, META_HISTORY_END))
        self.assertTrue(is_metadata_frame(comp_frame, META_HISTORY_COMPLETE))
        self.assertFalse(is_metadata_frame(start_frame, META_HISTORY_END))

    def test_history_end_data_extraction(self):
        # Frame with 10 bytes prefix padding (wires 7..16) then 8-byte end_data (wires 17..24)
        end_data_expected = b"\x11\x22\x33\x44\x55\x66\x77\x88"
        # Inner layout: [type:49, seq:0, meta_type:2] (3 bytes, wire 4..6)
        # padding: 10 bytes (wire 7..16)
        # end_data: 8 bytes (wire 17..24)
        padding = b"\x00" * 10
        end_frame = make_metadata_frame(META_HISTORY_END, payload=padding + end_data_expected)

        self.assertTrue(verify_whoop4_frame(end_frame))
        extracted = history_end_data_whoop4(end_frame)
        self.assertEqual(extracted, end_data_expected)

    def test_history_end_data_rejects_invalid_frames(self):
        # Truncated
        self.assertIsNone(history_end_data_whoop4(b"\xAA\x05\x00\x00\x31\x00\x02"))
        # Corrupt CRC
        end_frame = bytearray(make_metadata_frame(META_HISTORY_END, payload=b"\x00" * 18))
        end_frame[-1] ^= 0xFF
        self.assertIsNone(history_end_data_whoop4(bytes(end_frame)))

    def test_build_history_ack_whoop4(self):
        end_data = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        ack = build_history_ack_whoop4(end_data, seq=42)

        self.assertTrue(verify_whoop4_frame(ack))
        self.assertEqual(ack[0], 0xAA)
        self.assertEqual(ack[4], PACKET_COMMAND)
        self.assertEqual(ack[5], 42)
        self.assertEqual(ack[6], CMD_HISTORICAL_DATA_RESULT)
        # Payload starts at wire 7: 1 byte prefix 0x01 + 8 bytes end_data
        self.assertEqual(ack[7], 0x01)
        self.assertEqual(ack[8:16], end_data)

    def test_persist_before_ack_success(self):
        """When on_chunk_commit succeeds, trim ACK must be transmitted."""
        end_data = b"\x10\x20\x30\x40\x50\x60\x70\x80"
        end_frame = make_metadata_frame(META_HISTORY_END, payload=b"\x00" * 10 + end_data)

        commit_called = False

        def mock_commit(device_id, records, frames, trim_cursor):
            nonlocal commit_called
            commit_called = True
            self.assertEqual(trim_cursor, end_data.hex())

        device = Whoop4Device(on_chunk_commit=mock_commit)
        device._send_history_ack = AsyncMock()

        # Simulate arrival of HISTORY_END frame
        device._on_reassembled_frame("char-uuid", end_frame)

        self.assertTrue(commit_called)

    def test_persist_before_ack_suppresses_ack_on_failure(self):
        """When on_chunk_commit fails (e.g. DB error), ACK must be suppressed to prevent strap data loss."""
        end_data = b"\x10\x20\x30\x40\x50\x60\x70\x80"
        end_frame = make_metadata_frame(META_HISTORY_END, payload=b"\x00" * 10 + end_data)

        def mock_failing_commit(device_id, records, frames, trim_cursor):
            raise IOError("Simulated disk full or SQLite write failure")

        device = Whoop4Device(on_chunk_commit=mock_failing_commit)
        device._send_history_ack = AsyncMock()

        # Simulate arrival of HISTORY_END frame
        device._on_reassembled_frame("char-uuid", end_frame)

        # Confirm _send_history_ack was NEVER called
        device._send_history_ack.assert_not_called()


if __name__ == "__main__":
    unittest.main()
