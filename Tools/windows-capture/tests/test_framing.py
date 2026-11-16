"""Tests for WHOOP 4.0 packet framing, CRC checks, reassembly, and standard SIG decoders."""

import json
import unittest
from pathlib import Path

from noop_agent.ble.characteristics import CMD_GET_BATTERY_LEVEL
from noop_agent.ble.framing import (
    Reassembler,
    build_command_frame,
    crc8,
    crc32,
    parse_standard_battery,
    parse_standard_hr,
    verify_whoop4_frame,
)


class TestFraming(unittest.TestCase):

    def test_crc8_and_crc32(self):
        len_bytes = bytes([0x18, 0x00])
        self.assertEqual(crc8(len_bytes), 0xFF)

        payload = b"123456789"
        self.assertEqual(crc32(payload), 0xCBF43926)

    def test_build_and_verify_command_frame(self):
        frame = build_command_frame(cmd=CMD_GET_BATTERY_LEVEL, seq=42, payload=b"\x00")
        self.assertGreaterEqual(len(frame), 11)
        self.assertEqual(frame[0], 0xAA)
        self.assertEqual(frame[4], 35)  # PACKET_COMMAND
        self.assertEqual(frame[5], 42)  # seq
        self.assertEqual(frame[6], CMD_GET_BATTERY_LEVEL)
        self.assertTrue(verify_whoop4_frame(frame))

    def test_verify_against_frame_integrity_oracle(self):
        oracle_path = Path("Packages/WhoopProtocol/Tests/WhoopProtocolTests/Resources/frame_integrity_oracle.json")
        if not oracle_path.exists():
            return

        with open(oracle_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for case in data.get("cases", []):
            if case.get("family") != "whoop4":
                continue

            raw = bytes.fromhex(case["hex"])
            expected_verdict = case["verdict"]
            self.assertEqual(
                verify_whoop4_frame(raw),
                expected_verdict,
                f"Failed case {case['name']}",
            )

    def test_reassembler_fragmented_delivery(self):
        r = Reassembler()
        frame1 = build_command_frame(cmd=10, seq=1, payload=b"\x01\x02\x03\x04")
        frame2 = build_command_frame(cmd=20, seq=2, payload=b"\x05\x06")

        frag1 = frame1[:5]
        frag2 = frame1[5:10]
        frag3 = frame1[10:]

        self.assertEqual(r.feed(frag1), [])
        self.assertEqual(r.feed(frag2), [])
        out = r.feed(frag3)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], frame1)

        garbage = b"\x00\xff\xee\x12"
        out2 = r.feed(garbage + frame2)
        self.assertEqual(len(out2), 1)
        self.assertEqual(out2[0], frame2)

    def test_parse_standard_hr(self):
        bpm, rrs = parse_standard_hr(bytes([0x00, 72]))
        self.assertEqual(bpm, 72)
        self.assertEqual(rrs, [])

        bpm, rrs = parse_standard_hr(bytes([0x01, 0x04, 0x01]))
        self.assertEqual(bpm, 260)
        self.assertEqual(rrs, [])

        raw_1024 = bytes([1024 & 0xFF, (1024 >> 8) & 0xFF])
        bpm, rrs = parse_standard_hr(bytes([0x10, 80]) + raw_1024)
        self.assertEqual(bpm, 80)
        self.assertEqual(len(rrs), 1)
        self.assertEqual(rrs[0], 1000)

    def test_parse_standard_battery(self):
        self.assertEqual(parse_standard_battery(bytes([85])), 85)
        self.assertEqual(parse_standard_battery(bytes([0])), 0)
        self.assertEqual(parse_standard_battery(bytes([100])), 100)
        self.assertIsNone(parse_standard_battery(bytes([105])))
        self.assertIsNone(parse_standard_battery(b""))


if __name__ == "__main__":
    unittest.main()
