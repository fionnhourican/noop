"""Pure Python decoder for WHOOP 4.0 frames and standard SIG characteristics."""

import math
import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from noop_agent.ble.characteristics import (
    EVENT_BATTERY_LEVEL,
    PACKET_EVENT,
    PACKET_HISTORICAL_DATA,
    PACKET_METADATA,
    PACKET_REALTIME_DATA,
)
from noop_agent.ble.framing import verify_whoop4_frame
from noop_agent.protocol.models import (
    BatteryTelemetry,
    BiometricObservation,
    LiveHeartRate,
    ObservationProvenance,
)


def compute_rmssd(rr_intervals: List[int]) -> Optional[float]:
    """Compute Root-Mean-Square of Successive Differences (RMSSD) from positive R-R intervals."""
    clean_rr = [x for x in rr_intervals if x and x > 0]
    if len(clean_rr) < 2:
        return None
    diffs = [clean_rr[i + 1] - clean_rr[i] for i in range(len(clean_rr) - 1)]
    return math.sqrt(sum(d * d for d in diffs) / len(diffs))


class Whoop4Decoder:
    """Decodes WHOOP 4.0 frames into strongly typed observation models with full provenance."""

    def __init__(self, decoder_version: str = "1.0.0"):
        self.decoder_version = decoder_version

    def decode_frame(
        self,
        frame: bytes,
        device_id: str,
        raw_frame_id: Optional[int] = None,
        reception_utc: Optional[datetime] = None,
    ) -> List[ObservationProvenance]:
        """Validate envelope integrity and decode observation records.

        Emits list of `ObservationProvenance` records ready for durable queue storage.
        """
        if reception_utc is None:
            reception_utc = datetime.now(timezone.utc)

        # Integrity check: SOF, declared length, CRC-8 header, CRC-32 trailer
        if not verify_whoop4_frame(frame):
            return [
                ObservationProvenance(
                    device_id=device_id,
                    record_type="corrupt_frame",
                    timestamp_utc=reception_utc,
                    reception_utc=reception_utc,
                    data_origin="unknown",
                    validation_status="corrupt",
                    protocol_version=4,
                    decoder_version=self.decoder_version,
                    raw_frame_id=raw_frame_id,
                    metadata={"frame_len": len(frame), "frame_hex": frame.hex()[:32]},
                )
            ]

        inner_type = frame[4]
        seq = frame[5]
        limit = len(frame) - 4  # CRC-32 trailer starts at len(frame) - 4

        results: List[ObservationProvenance] = []

        # ======================================================================
        # 1. REALTIME DATA (Packet Type 40)
        # ======================================================================
        if inner_type == PACKET_REALTIME_DATA:
            if len(frame) < 14:
                return results

            ts_raw = struct.unpack_from("<I", frame, 6)[0]
            subseconds = struct.unpack_from("<H", frame, 10)[0]
            hr_val = frame[12]
            rr_count = frame[13]

            # Convert timestamp: if > 1_000_000_000, treat as unix epoch, otherwise reference from now
            if ts_raw > 1_000_000_000:
                obs_time = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            else:
                obs_time = reception_utc

            rr_intervals: List[int] = []
            for i in range(rr_count):
                off = 14 + i * 2
                if off + 2 <= limit:
                    rr = struct.unpack_from("<H", frame, off)[0]
                    if rr > 0:
                        rr_intervals.append(rr)

            rmssd = compute_rmssd(rr_intervals)

            # Emit normalized heart rate record
            if hr_val > 0:
                results.append(
                    ObservationProvenance(
                        device_id=device_id,
                        record_type="heart_rate",
                        timestamp_utc=obs_time,
                        reception_utc=reception_utc,
                        data_origin="live",
                        validation_status="valid",
                        protocol_version=4,
                        decoder_version=self.decoder_version,
                        raw_frame_id=raw_frame_id,
                        value=hr_val,
                        unit="bpm",
                        metadata={
                            "subseconds": subseconds,
                            "raw_timestamp": ts_raw,
                            "seq": seq,
                        },
                    )
                )

            # Emit biometric record if intervals or telemetry present
            if rr_intervals or hr_val > 0:
                results.append(
                    ObservationProvenance(
                        device_id=device_id,
                        record_type="biometric",
                        timestamp_utc=obs_time,
                        reception_utc=reception_utc,
                        data_origin="live",
                        validation_status="valid",
                        protocol_version=4,
                        decoder_version=self.decoder_version,
                        raw_frame_id=raw_frame_id,
                        value={
                            "heart_rate": hr_val,
                            "rr_count": len(rr_intervals),
                            "rr_intervals_ms": rr_intervals,
                            "rmssd": rmssd,
                            "subseconds": subseconds,
                        },
                        metadata={"seq": seq, "raw_timestamp": ts_raw},
                    )
                )

        # ======================================================================
        # 2. HISTORICAL DATA (Packet Type 47)
        # ======================================================================
        elif inner_type == PACKET_HISTORICAL_DATA:
            hist_ver = seq  # On WHOOP 4.0, sequence byte indicates the DSP layout version
            if len(frame) < 23:
                return results

            unix_sec = struct.unpack_from("<I", frame, 11)[0]
            obs_time = (
                datetime.fromtimestamp(unix_sec, tz=timezone.utc)
                if unix_sec > 1_000_000_000
                else reception_utc
            )

            hr_val = frame[21]
            rr_count = frame[22]

            rr_intervals = []
            for i in range(min(rr_count, 6)):
                off = 23 + i * 2
                if off + 2 <= limit and off + 2 <= 33:
                    rr = struct.unpack_from("<H", frame, off)[0]
                    if rr > 0:
                        rr_intervals.append(rr)

            rmssd = compute_rmssd(rr_intervals)

            # Extract full biometric DSP fields if version 24 or 12
            biometric_payload: Dict[str, Any] = {
                "unix": unix_sec,
                "heart_rate": hr_val,
                "rr_count": len(rr_intervals),
                "rr_intervals_ms": rr_intervals,
                "rmssd": rmssd,
                "hist_version": hist_ver,
            }

            if hist_ver in (24, 12) and len(frame) >= 84:
                biometric_payload["ppg_green"] = struct.unpack_from("<H", frame, 33)[0]
                biometric_payload["ppg_red_ir"] = struct.unpack_from("<H", frame, 35)[0]

                gx, gy, gz = struct.unpack_from("<fff", frame, 40)
                biometric_payload["gravity_x"] = gx
                biometric_payload["gravity_y"] = gy
                biometric_payload["gravity_z"] = gz

                biometric_payload["skin_contact"] = frame[55]

                biometric_payload["spo2_red_adc"] = struct.unpack_from("<H", frame, 68)[0]
                biometric_payload["spo2_ir_adc"] = struct.unpack_from("<H", frame, 70)[0]
                biometric_payload["skin_temp_raw"] = struct.unpack_from("<H", frame, 72)[0]
                biometric_payload["resp_rate_raw"] = struct.unpack_from("<H", frame, 80)[0]
                biometric_payload["signal_quality"] = struct.unpack_from("<H", frame, 82)[0]

            # Emit normalized heart rate record
            if hr_val > 0:
                results.append(
                    ObservationProvenance(
                        device_id=device_id,
                        record_type="heart_rate",
                        timestamp_utc=obs_time,
                        reception_utc=reception_utc,
                        data_origin="historical",
                        validation_status="valid",
                        protocol_version=4,
                        decoder_version=self.decoder_version,
                        raw_frame_id=raw_frame_id,
                        value=hr_val,
                        unit="bpm",
                        metadata={"hist_version": hist_ver, "unix": unix_sec},
                    )
                )

            # Emit biometric observation record
            results.append(
                ObservationProvenance(
                    device_id=device_id,
                    record_type="biometric",
                    timestamp_utc=obs_time,
                    reception_utc=reception_utc,
                    data_origin="historical",
                    validation_status="valid",
                    protocol_version=4,
                    decoder_version=self.decoder_version,
                    raw_frame_id=raw_frame_id,
                    value=biometric_payload,
                    metadata={"hist_version": hist_ver},
                )
            )

        # ======================================================================
        # 3. EVENT (Packet Type 48)
        # ======================================================================
        elif inner_type == PACKET_EVENT:
            if len(frame) < 12:
                return results

            event_code = frame[6]
            event_ts = struct.unpack_from("<I", frame, 8)[0]
            obs_time = (
                datetime.fromtimestamp(event_ts, tz=timezone.utc)
                if event_ts > 1_000_000_000
                else reception_utc
            )

            if event_code == EVENT_BATTERY_LEVEL and len(frame) >= 27:
                soc_raw = struct.unpack_from("<H", frame, 17)[0]
                soc = (soc_raw / 10.0) if soc_raw <= 1100 else None

                mv = struct.unpack_from("<H", frame, 21)[0]
                if not (3000 <= mv <= 4300):
                    mv = None

                ch_byte = frame[26]
                charging = bool(ch_byte & 1)

                results.append(
                    ObservationProvenance(
                        device_id=device_id,
                        record_type="battery",
                        timestamp_utc=obs_time,
                        reception_utc=reception_utc,
                        data_origin="live",
                        validation_status="valid",
                        protocol_version=4,
                        decoder_version=self.decoder_version,
                        raw_frame_id=raw_frame_id,
                        value={
                            "soc_percent": soc,
                            "millivolts": mv,
                            "is_charging": charging,
                        },
                        unit="percent",
                        metadata={"event_code": event_code, "raw_ts": event_ts},
                    )
                )

        # ======================================================================
        # 4. METADATA (Packet Type 49)
        # ======================================================================
        elif inner_type == PACKET_METADATA:
            if len(frame) >= 7:
                meta_type = frame[6]
                trim_cursor = None
                end_data_hex = None
                if len(frame) >= 25:
                    trim_cursor = struct.unpack_from("<I", frame, 17)[0]
                    end_data_hex = frame[17:25].hex()

                results.append(
                    ObservationProvenance(
                        device_id=device_id,
                        record_type="metadata",
                        timestamp_utc=reception_utc,
                        reception_utc=reception_utc,
                        data_origin="historical",
                        validation_status="valid",
                        protocol_version=4,
                        decoder_version=self.decoder_version,
                        raw_frame_id=raw_frame_id,
                        value={
                            "meta_type": meta_type,
                            "trim_cursor": trim_cursor,
                            "end_data_hex": end_data_hex,
                        },
                        metadata={"meta_type": meta_type},
                    )
                )

        return results
