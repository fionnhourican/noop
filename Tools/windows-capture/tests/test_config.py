"""Tests for agent configuration loading and credential manager fallback."""

import tempfile
import unittest
from pathlib import Path

from noop_agent.config import AgentConfig, DeviceConfig, ServerConfig


class TestConfig(unittest.TestCase):

    def test_default_config_creation(self):
        cfg = AgentConfig()
        self.assertEqual(cfg.device.name, "WHOOP 4.0")
        self.assertEqual(cfg.server.sync_interval_seconds, 30)
        self.assertTrue(cfg.ble.auto_pair)
        self.assertEqual(cfg.logging.level, "INFO")

    def test_load_config_from_yaml_file(self):
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

            loaded = AgentConfig.load(cfg_path)
            self.assertEqual(loaded.device.address, "00:11:22:33:44:55")
            self.assertEqual(loaded.device.name, "My Strap")
            self.assertEqual(loaded.server.url, "https://tailnet.server/api/v1")
            self.assertEqual(loaded.server.token, "secret_yaml_token")
            self.assertEqual(loaded.server.sync_interval_seconds, 45)
            self.assertFalse(loaded.ble.auto_pair)
            self.assertEqual(loaded.logging.level, "DEBUG")


if __name__ == "__main__":
    unittest.main()
