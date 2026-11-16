# NOOP Windows 11 Collector Agent

A background Windows 11 application that connects directly to a WHOOP 4.0 band over Bluetooth Low Energy (BLE), stages observations in a durable local SQLite database, and synchronizes batches to your home server over Tailscale.

## Features

- **Direct BLE Gateway**: Connects directly to the strap using Python `bleak` over Windows WinRT.
- **Dual Async Pipelines**: Live Heart Rate streaming (`2a37`) and historical flash memory offload (`SEND_HISTORICAL_DATA`).
- **Durable Local Persistence**: Records are committed to SQLite (`%LOCALAPPDATA%\NOOP\collector.sqlite`) in WAL mode with persist-before-ACK guarantees.
- **Single-Instance Protection**: Enforced via Windows Named Mutex (`Global\NOOP_HomeLab_Collector_Mutex`).
- **System Tray Telemetry**: Real-time visual status indicator (Green/Yellow/Grey/Red) and control menu.
- **Automatic Startup**: Runs windowlessly (`pythonw.exe`) in the interactive user session at Windows logon via Task Scheduler.

---

## Quick Start

### 1. Prerequisites
- **Windows 11** with Bluetooth Low Energy (BLE 4.2+ or 5.0+).
- **Python 3.12+** installed (check **"Add python.exe to PATH"** during installation).
- **Pair your WHOOP 4.0 in Windows**:
  - Double-tap the top of the band until the side LED pulses blue.
  - In Windows: **Settings → Bluetooth & devices → Add device → Bluetooth** and pair with the WHOOP.

### 2. Configure
Copy or edit `config.yaml` in this folder:

```yaml
server:
  url: "https://your-server.tailnet-name.ts.net/api/v1"
  ingestion_token: "your_secret_ingestion_token"
  sync_interval_seconds: 5
  batch_size: 100
  verify_ssl: false   # Recommended for internal Tailscale mesh routing

ble:
  target_device_name: "WHOOP"
  auto_discover: true
  scan_timeout_seconds: 15.0
  reconnect_interval_seconds: 5.0
```

### 3. Test Run
Run `run.bat` in Command Prompt or PowerShell:
```powershell
.\run.bat
```
*(Dependencies are verified/installed automatically and the collector will connect and sync initial batches).*

### 4. Install Background Startup Service
To register the agent as an automatic background service (no terminal window needed):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\install.ps1
```

The installer:
1. Secures `%LOCALAPPDATA%\NOOP\` permissions to your Windows account only.
2. Copies `config.yaml` into `%LOCALAPPDATA%\NOOP\config.yaml`.
3. Registers `NOOP_HomeLab_Collector` in Windows Task Scheduler.
4. Starts the background service immediately via `pythonw.exe`.

### 5. Management & Logs
- **System Tray**: Right-click the NOOP icon in your taskbar to force sync, pause/resume, view logs, or exit.
- **Log file**: `%LOCALAPPDATA%\NOOP\logs\collector.log`.
- **Uninstall**: Run `.\uninstall.ps1` in PowerShell.
