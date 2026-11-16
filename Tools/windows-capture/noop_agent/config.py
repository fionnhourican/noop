"""Configuration loading and Windows Credential Manager integration."""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

SERVICE_NAME = "NOOP_HomeLab_Ingestion"
USERNAME = "collector"


def get_noop_app_data_dir() -> Path:
    """Resolve %LOCALAPPDATA%\\NOOP on Windows or fallback on other platforms."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        else:
            base = Path.home() / "AppData" / "Local"
    else:
        # Check XDG_DATA_HOME or fallback to ~/.noop or /tmp
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            base = Path(xdg)
        else:
            base = Path.home() / ".local" / "share"

    noop_dir = base / "NOOP"
    try:
        noop_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Read-only or sandbox environment; fallback to current dir
        noop_dir = Path(".noop_data")
        try:
            noop_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    return noop_dir


@dataclass
class DeviceConfig:
    address: Optional[str] = None
    name: str = "WHOOP 4.0"
    model: str = "whoop4"


@dataclass
class ServerConfig:
    url: str = "http://127.0.0.1:8080/api/v1"
    token: Optional[str] = None
    sync_interval_seconds: int = 30
    batch_size: int = 100
    verify_ssl: bool = True


@dataclass
class BleConfig:
    scan_timeout: float = 10.0
    min_retry_delay: float = 2.0
    max_retry_delay: float = 60.0
    auto_pair: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class AgentConfig:
    device: DeviceConfig = field(default_factory=DeviceConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    ble: BleConfig = field(default_factory=BleConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    data_dir: Path = field(default_factory=get_noop_app_data_dir)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "collector.sqlite"

    @property
    def log_path(self) -> Path:
        log_dir = self.data_dir / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return log_dir / "collector.log"

    def get_ingestion_token(self) -> Optional[str]:
        """Fetch token from Windows Credential Manager or fallback to config."""
        try:
            import keyring
            cred_token = keyring.get_password(SERVICE_NAME, USERNAME)
            if cred_token:
                return cred_token
        except Exception:
            pass

        return self.server.token

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AgentConfig":
        """Load configuration from YAML/JSON file or default paths."""
        if config_path and Path(config_path).exists():
            path_to_load = Path(config_path)
        else:
            default_path = get_noop_app_data_dir() / "config.yaml"
            if default_path.exists():
                path_to_load = default_path
            else:
                local_cand = Path("config.yaml")
                if local_cand.exists():
                    path_to_load = local_cand
                else:
                    return cls()

        data: Dict[str, Any] = {}
        try:
            with open(path_to_load, "r", encoding="utf-8") as f:
                content = f.read()
                try:
                    import yaml
                    data = yaml.safe_load(content) or {}
                except ImportError:
                    data = json.loads(content)
        except Exception:
            data = {}

        dev_data = data.get("device", {})
        srv_data = data.get("server", {})
        ble_data = data.get("ble", {})
        log_data = data.get("logging", {})

        return cls(
            device=DeviceConfig(
                address=dev_data.get("address"),
                name=dev_data.get("name", "WHOOP 4.0"),
                model=dev_data.get("model", "whoop4"),
            ),
            server=ServerConfig(
                url=srv_data.get("url", "http://127.0.0.1:8080/api/v1"),
                token=srv_data.get("token"),
                sync_interval_seconds=srv_data.get("sync_interval_seconds", 30),
                batch_size=srv_data.get("batch_size", 100),
                verify_ssl=srv_data.get("verify_ssl", True),
            ),
            ble=BleConfig(
                scan_timeout=ble_data.get("scan_timeout", 10.0),
                min_retry_delay=ble_data.get("min_retry_delay", 2.0),
                max_retry_delay=ble_data.get("max_retry_delay", 60.0),
                auto_pair=ble_data.get("auto_pair", True),
            ),
            logging=LoggingConfig(
                level=log_data.get("level", "INFO"),
            ),
        )
