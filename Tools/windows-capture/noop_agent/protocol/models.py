"""Data models and provenance contracts for decoded WHOOP observations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ObservationProvenance:
    """Provenance tracking envelope strictly complying with Home Lab contract."""

    device_id: str
    record_type: str
    timestamp_utc: datetime
    reception_utc: datetime
    data_origin: str = "live"              # "live" or "historical"
    validation_status: str = "valid"       # "valid", "corrupt", "unverified"
    protocol_version: int = 4
    decoder_version: str = "1.0.0"
    raw_frame_id: Optional[int] = None
    value: Any = None
    unit: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LiveHeartRate:
    """Decoded live heart rate and inter-beat intervals."""

    bpm: int
    rr_intervals_ms: List[int] = field(default_factory=list)
    subseconds: Optional[int] = None
    source: str = "whoop_realtime"         # "whoop_realtime" or "sig_hr"


@dataclass
class BatteryTelemetry:
    """Battery state of charge, voltage, and charging indicator."""

    soc_percent: float
    millivolts: Optional[int] = None
    is_charging: Optional[bool] = None
    source: str = "whoop_event"            # "whoop_event" or "sig_battery"


@dataclass
class BiometricObservation:
    """Per-second multi-sensor observation (WHOOP 4.0 DSP record layout).

    All optical and accelerometer values maintain strict provenance:
    - Raw ADC channels are preserved without unverified physical conversion.
    - Accelerometer gravity values are float32 in units of g.
    - Skin temperature is retained as raw ADC.
    """

    unix: int
    heart_rate: Optional[int] = None
    rr_count: int = 0
    rr_intervals_ms: List[int] = field(default_factory=list)
    rmssd: Optional[float] = None
    gravity_x: Optional[float] = None
    gravity_y: Optional[float] = None
    gravity_z: Optional[float] = None
    skin_contact: Optional[int] = None
    spo2_red_adc: Optional[int] = None
    spo2_ir_adc: Optional[int] = None
    skin_temp_raw: Optional[int] = None
    resp_rate_raw: Optional[int] = None
    ppg_green: Optional[int] = None
    ppg_red_ir: Optional[int] = None
    signal_quality: Optional[int] = None
    hist_version: int = 24


@dataclass
class DeviceInfo:
    """Identified strap hardware, firmware, and serial credentials."""

    address: str
    name: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    model: str = "whoop4"
