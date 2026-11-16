"""CLI entrypoint for NOOP Windows Collector."""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

from noop_agent.config import AgentConfig
from noop_agent.logging_config import setup_logging
from noop_agent.supervisor import AgentSupervisor


def main():
    parser = argparse.ArgumentParser(description="NOOP Windows 11 BLE Background Collector")
    parser.add_argument("--config", "-c", type=str, help="Path to config.yaml")
    parser.add_argument("--headless", action="store_true", help="Run without system tray icon")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    config = AgentConfig.load(config_path)

    # Setup structured rotating file logger
    setup_logging(config.log_path, config.logging.level)

    supervisor = AgentSupervisor(config, enable_tray=not args.headless)

    # Attach signal handlers for graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def sig_handler():
        supervisor.stop_event.set()

    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, sig_handler)
        loop.add_signal_handler(signal.SIGTERM, sig_handler)

    try:
        loop.run_until_complete(supervisor.start())
    except KeyboardInterrupt:
        loop.run_until_complete(supervisor.shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
