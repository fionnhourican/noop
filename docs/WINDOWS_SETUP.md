# NOOP Home Lab — Windows 11 Collector Setup Guide

This guide walks through configuring your Windows 11 laptop as the Bluetooth Low Energy gateway for NOOP Home Lab.

---

## 1. Prerequisites

- **Windows 11** (x86-64 or ARM64) with Bluetooth Low Energy (BLE 4.2+ or 5.0+) hardware.
- **Python 3.12+** installed (check "Add python.exe to PATH" during installation).
- **WHOOP 4.0** band (charged and awake).
- **Tailscale** installed and connected on Windows (joining the same Tailnet as your home server).

---

## 2. Windows Bluetooth & Strap Pairing

1. **Disconnect from Mobile Phone**: Turn off Bluetooth on your smartphone or "Forget" the WHOOP 4.0 to ensure the band is advertising freely.
2. **Trigger Pairing Mode**: Double tap the top of the WHOOP 4.0 until the side LED pulses blue.
3. **Windows Bluetooth Settings**:
   - Open **Settings** -> **Bluetooth & devices**.
   - Select **Add device** -> **Bluetooth**.
   - When the WHOOP 4.0 appears, click to pair. Windows will establish bonding.

---

## 3. Installing the Collector Agent

Open PowerShell as your normal user (not elevated Administrator):

```powershell
# Navigate to the repository
cd C:\path\to\noop\Tools\windows-capture

# Install required dependencies
pip install -r requirements.txt

# Run the installer script
.\install.ps1 -ServerUrl "https://your-server-name.your-tailnet.ts.net/api/v1" -IngestionToken "your_secret_bearer_token"
```

The installer script will:
1. Create `%LOCALAPPDATA%\NOOP\` with locked filesystem permissions (accessible only by your Windows user account).
2. Generate `%LOCALAPPDATA%\NOOP\config.yaml`.
3. Securely store your API ingestion Bearer token in Windows Credential Manager under `NOOP_HomeLab_Ingestion`.
4. Register a Task Scheduler job that launches the agent windowlessly (`pythonw.exe`) at user logon.

---

## 4. Running and Managing the Agent

### Start the Collector
```powershell
Start-ScheduledTask -TaskName "NOOP_HomeLab_Collector"
```

Or start manually in interactive mode:
```powershell
python -m noop_agent.main
```

### System Tray Status Indicators
Once running, the NOOP icon appears in your system tray:
- **Green**: Connected to WHOOP 4.0 / Collecting data.
- **Yellow**: Scanning for strap or synchronizing with server.
- **Grey**: Disconnected / Waiting for strap to enter range.
- **Red**: Error (check log file).

Right-click the tray icon to:
- **Synchronise Now**: Forces an immediate upload of pending queued records.
- **Pause / Resume**: Temporarily suspends BLE polling and collection.
- **View Logs**: Opens `%LOCALAPPDATA%\NOOP\logs\collector.log`.
- **Open Configuration**: Opens `%LOCALAPPDATA%\NOOP\config.yaml`.
- **Exit**: Cleanly shuts down the supervisor and releases the single-instance mutex.

---

## 5. Troubleshooting

- **Logs Location**: `%LOCALAPPDATA%\NOOP\logs\collector.log`
- **Database Location**: `%LOCALAPPDATA%\NOOP\collector.sqlite`
- **Duplicate Instance Error**: If the agent reports `Another instance is already running`, check Task Manager for existing `pythonw.exe` processes or remove `%LOCALAPPDATA%\NOOP\agent.lock`.

---

## 6. Uninstallation

To cleanly stop the agent and remove it from automatic startup:

```powershell
.\uninstall.ps1
```

To also delete your local SQLite database:

```powershell
.\uninstall.ps1 -RemoveData
```
