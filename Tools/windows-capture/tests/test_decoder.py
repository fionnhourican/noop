"""Tests for pure Python WHOOP 4.0 frame decoder and oracle parity."""

import unittest
from noop_agent.protocol.decoder import Whoop4Decoder, compute_rmssd


class TestDecoder(unittest.TestCase):

    def test_compute_rmssd(self):
        # Consecutive intervals: 800, 850, 820
        # Diffs: +50, -30 -> squares: 2500, 900 -> mean: 1700 -> sqrt: ~41.23
        rrs = [800, 850, 820]
        rmssd = compute_rmssd(rrs)
        self.assertIsNotNone(rmssd)
        self.assertEqual(round(rmssd, 2), 41.23)

        # Less than 2 positive intervals
        self.assertIsNone(compute_rmssd([]))
        self.assertIsNone(compute_rmssd([800]))
        self.assertIsNone(compute_rmssd([0, 0]))

    def test_decode_whoop4_v24_real_worn_oracle(self):
        """Test against golden frame from decoder_oracle.json."""
        hex_str = (
            "aa6400a12f18054c1c0a023ed0266a5037805418016d022b0234020000000000006b07ff0085593c1f"
            "65cebed7b3e63eb85a5f3f000080401f65cebed7b3e63eb85a5f3f500264025d03640229014009010c"
            "020c00000000000f0001c4020000000000008fdeb278"
        )
        frame = bytes.fromhex(hex_str)

        decoder = Whoop4Decoder()
        records = decoder.decode_frame(frame, device_id="test_strap")

        self.assertGreaterEqual(len(records), 1)
        # Check normalized heart rate record
        hr_recs = [r for r in records if r.record_type == "heart_rate"]
        self.assertEqual(len(hr_recs), 1)
        self.assertEqual(hr_recs[0].value, 109)
        self.assertEqual(hr_recs[0].data_origin, "historical")
        self.assertEqual(hr_recs[0].validation_status, "valid")

        # Check biometric observation record
        bio_recs = [r for r in records if r.record_type == "biometric"]
        self.assertEqual(len(bio_recs), 1)
        bio = bio_recs[0].value
        self.assertEqual(bio["unix"], 1780928574)
        self.assertEqual(bio["heart_rate"], 109)
        self.assertEqual(bio["rr_count"], 2)
        self.assertEqual(bio["rr_intervals_ms"], [555, 564])
        self.assertEqual(bio["hist_version"], 24)

        # Gravity components
        gx, gy, gz = bio["gravity_x"], bio["gravity_y"], bio["gravity_z"]
        mag = (gx * gx + gy * gy + gz * gz) ** 0.5
        self.assertEqual(round(mag, 1), 1.1)

    def test_decode_realtime_frame(self):
        """Test against valid realtime frame (type 40)."""
        hex_str = "aa1800ff28020f3de10128663c0000000000000000000000da855212"
        frame = bytes.fromhex(hex_str)

        decoder = Whoop4Decoder()
        records = decoder.decode_frame(frame, device_id="test_strap")

        self.assertGreaterEqual(len(records), 1)
        hr_recs = [r for r in records if r.record_type == "heart_rate"]
        self.assertEqual(len(hr_recs), 1)
        self.assertEqual(hr_recs[0].value, 60)
        self.assertEqual(hr_recs[0].unit, "bpm")
        self.assertEqual(hr_recs[0].data_origin, "live")

    def test_corrupt_frame_rejection(self):
        # Bad CRC trailer
        hex_str = "aa07006b3100012366efaa"
        frame = bytes.fromhex(hex_str)

        decoder = Whoop4Decoder()
        records = decoder.decode_frame(frame, device_id="test_strap")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].validation_status, "corrupt")


if __name__ == "__main__":
    unittest.main()
