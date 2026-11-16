"""Tests for agent configuration loading and credential manager fallback."""

import os
import tempfile
from pathlib import Path
from noop_agent.config import CollectorConfig, load_config


def test_default_config_creation():
    cfg = CollectorConfig()
    assert cfg.device.name == "WHOOP 4.0"
    assert cfg.server.sync_interval_seconds == 30
    assert cfg.ble.auto_pair is True
    assert cfg.logging.level == "INFO"


def test_load_config_from_yaml_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "config.yaml"
        cfg_path.write_text(
            """
device:
  address: "00:11:22:33:44:55"
  name: "My Strap"
server:
  url: "https://tailnet.server/api/v1"
  token: "secret_yaml_token"
  sync_interval_seconds: 45
ble:
  auto_pair: false
logging:
  level: "DEBUG"
""",
            encoding="utf-8",
        )

        loaded = load_config(cfg_path)
        assert loaded.device.address == "00:11:22:33:44:55"
        assert loaded.device.name == "My Strap"
        assert loaded.server.url == "https://tailnet.server/api/v1"
        assert loaded.server.token == "secret_yaml_token"
        assert loaded.server.sync_interval_seconds == 45
        assert loaded.ble.auto_pair is False
        assert loaded.logging.level == "DEBUG"
