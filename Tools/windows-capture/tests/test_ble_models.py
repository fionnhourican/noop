"""Tests verifying data provenance contracts and observation models."""

import unittest
from datetime import datetime, timezone

from noop_agent.protocol.models import (
    BatteryTelemetry,
    BiometricObservation,
    DeviceInfo,
    LiveHeartRate,
    ObservationProvenance,
)


class TestBleModels(unittest.TestCase):

    def test_observation_provenance_contract(self):
        now = datetime.now(timezone.utc)
        obs = ObservationProvenance(
            device_id="EA:00:11:22:33:44",
            record_type="heart_rate",
            timestamp_utc=now,
            reception_utc=now,
            data_origin="live",
            validation_status="valid",
            protocol_version=4,
            decoder_version="1.0.0",
            raw_frame_id=123,
            value=75,
            unit="bpm",
            metadata={"source": "sig_2a37"},
        )

        self.assertEqual(obs.device_id, "EA:00:11:22:33:44")
        self.assertEqual(obs.record_type, "heart_rate")
        self.assertIn(obs.data_origin, ("live", "historical"))
        self.assertIn(obs.validation_status, ("valid", "corrupt", "unverified"))
        self.assertEqual(obs.protocol_version, 4)
        self.assertEqual(obs.decoder_version, "1.0.0")
        self.assertEqual(obs.raw_frame_id, 123)
        self.assertEqual(obs.value, 75)
        self.assertEqual(obs.unit, "bpm")

    def test_biometric_observation_nullable_fields(self):
        bio = BiometricObservation(unix=1700000000, heart_rate=65)
        self.assertEqual(bio.unix, 1700000000)
        self.assertEqual(bio.heart_rate, 65)
        self.assertIsNone(bio.spo2_red_adc)
        self.assertIsNone(bio.skin_temp_raw)
        self.assertIsNone(bio.gravity_x)


if __name__ == "__main__":
    unittest.main()
