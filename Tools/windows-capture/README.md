# NOOP Windows 11 Collector Agent

A background Windows 11 application that connects directly to a WHOOP 4.0 band over Bluetooth Low Energy (BLE), stages observations in a durable local SQLite database, and synchronizes to your home server over Tailscale.

## Features

- **Direct BLE Gateway**: Connects directly to the strap using Python `bleak` over Windows WinRT.
- **Durable Local Persistence**: Records are committed to SQLite (`%LOCALAPPDATA%\NOOP\collector.sqlite`) in WAL mode before network transfer.
- **Single-Instance Protection**: Enforced via Windows Named Mutex (`Global\NOOP_HomeLab_Collector_Mutex`).
- **Decoupled System Tray**: Real-time visual status indicator (Green/Yellow/Grey/Red) and management menu.
- **Secure Credentials**: API Bearer token stored in Windows Credential Manager (`keyring`).
- **Automatic Startup**: Runs in the interactive user session at Windows logon via Task Scheduler.

## Directory Layout

```
Tools/windows-capture/
|-- noop_agent/
|   |-- ble/             # BLE GATT transport & characteristics (Phase 4)
|   |-- protocol/        # WHOOP 4.0 v24/v25 packet decoding (Phase 4)
|   |-- storage/         # SQLite WAL persistence & durable queue
|   |-- sync/            # HTTPX batch synchronizer (Phase 5)
|   |-- tray/            # Pystray tray application & icon generation
|   |-- config.py        # Configuration & credential manager
|   |-- logging_config.py# Rotating file logging
|   |-- supervisor.py    # Subsystem supervisor & single-instance mutex
|   |-- main.py          # Application CLI entrypoint
|-- tests/               # Automated unit tests
|-- install.ps1          # Automatic startup Task Scheduler installer
|-- uninstall.ps1        # Uninstaller
|-- requirements.txt     # Python dependencies
|-- pyproject.toml       # Package metadata
```

## Quick Start

1. Install Python 3.12+ from [python.org](https://www.python.org/).
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run the installer:
   ```powershell
   .\install.ps1 -ServerUrl "https://whoop-server.your-tailnet.ts.net/api/v1" -IngestionToken "your_secret_token"
   ```
4. Start the scheduled task or run directly:
   ```powershell
   python -m noop_agent.main
   ```
