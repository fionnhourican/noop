# NOOP Home Lab — Self-Hosted WHOOP 4.0 Platform

A self-hosted, offline-first companion system for the WHOOP 4.0 fitness band.

```
WHOOP 4.0 (BLE)  --->  Windows 11 Collector Agent  --->  Linux Home Server (Docker + Tailscale)
                                                                 │
                                                       Web Dashboard & API
                                              (PostgreSQL 17 + FastAPI + React)
```

1. **Windows 11 Collector Agent** (`Tools/windows-capture/`):
   - Direct Bluetooth LE communication using Bleak.
   - Dual pipelines: Live Heart Rate (`2a37`) & Historical Offload (`SEND_HISTORICAL_DATA`).
   - Durable local SQLite storage (`%LOCALAPPDATA%\NOOP\collector.sqlite`) in WAL mode with persist-before-ACK guarantees.
   - Background system tray application with single-instance mutex, status indicators, and Windows Task Scheduler auto-start.
   - Resilient sync with exponential backoff and jitter.

2. **Linux Home Server** (`homelab/`):
   - **Docker Compose**: Orchestrates PostgreSQL 17, FastAPI backend, and React/Nginx frontend.
   - **PostgreSQL 17**: Relational storage for immutable raw frames, source records, and normalized biometric samples.
   - **FastAPI Backend**: Authenticated batch ingestion endpoint, ported NOOP analytics (RMSSD, z-score recovery, Banister TRIMP day strain), and WebSockets for real-time live pulse.
   - **React Dashboard**: Modern web interface built with React 18, Vite, TypeScript, and Tailwind CSS. Features real-time WebSocket heart rate pulse, daily recovery gauge (0-100%), logarithmic day strain meter (0-21.0), sleep architecture breakdown, workouts list, and Windows collector telemetry.
   - **Tailscale Serve**: Encrypted remote access without exposing ports to the public internet.

---

## Complete Setup Guide

Setting up NOOP Home Lab takes about 10 minutes across two machines:
- **Machine A (Home Server)**: Any Linux machine (Ubuntu, Debian, Raspberry Pi, Unraid) with Docker.
- **Machine B (Windows 11 Laptop/PC)**: With Bluetooth LE hardware and Python 3.12+.

---

### Step 1: Deploy the Home Server (Linux)

#### 1.1 Clone the Repository
```bash
git clone --depth 1 https://github.com/fionnhourican/noop.git ~/noop-homelab
cd ~/noop-homelab/homelab
```

#### 1.2 Configure Secrets
Copy the environment template:
```bash
cp .env.example .env
```
Edit `.env` (e.g. `nano .env`) and set your secrets:
```ini
POSTGRES_USER=noop
POSTGRES_PASSWORD=your_secure_postgres_password
POSTGRES_DB=noop_homelab

# Secret Bearer token for Windows collector upload:
INGESTION_TOKEN=your_random_secret_ingestion_token_here

# Secret Bearer token to unlock the Web Dashboard:
DASHBOARD_TOKEN=your_random_secret_dashboard_token_here

ENVIRONMENT=production
```

#### 1.3 Start Services
```bash
docker compose up -d --build
```

Verify that the health check passes:
```bash
curl -f http://127.0.0.1:8080/api/v1/health
```
*(Should return `{"status":"healthy",...}`)*

#### 1.4 Expose via Tailscale Serve
For secure remote access across your devices without opening router ports:
```bash
sudo tailscale serve --bg http://127.0.0.1:8080
```
Note your Tailscale HTTPS URL (e.g. `https://your-server.tailnet-name.ts.net`).

---

### Step 2: Set Up the Windows 11 Bluetooth Collector

The Windows agent connects to your WHOOP strap over Bluetooth, saves observations locally in SQLite, and syncs batches over Tailscale to your home server.

#### 2.1 Prerequisites
1. **Python 3.12+**: Download and install from [python.org](https://www.python.org/) (ensure **"Add python.exe to PATH"** is checked during setup).
2. **Tailscale**: Ensure Tailscale is installed on Windows and logged into the same Tailnet as your home server.
3. **Pair your WHOOP 4.0 in Windows**:
   - Disconnect your WHOOP from your phone (or turn phone Bluetooth off).
   - Double-tap the top of the WHOOP 4.0 until the side LED pulses blue (pairing mode).
   - Open **Windows Settings → Bluetooth & devices → Add device → Bluetooth**.
   - Select your WHOOP 4.0 and complete pairing.

#### 2.2 Configure the Agent
Open PowerShell or File Explorer and navigate to `Tools\windows-capture`:
```powershell
cd \\wsl.localhost\Ubuntu\home\owner\personal\noop\Tools\windows-capture
# (or C:\path\to\noop\Tools\windows-capture if cloned directly on Windows)
```

Create or edit `config.yaml`:
```yaml
server:
  url: "https://your-server.tailnet-name.ts.net/api/v1"
  ingestion_token: "your_random_secret_ingestion_token_here"  # Match INGESTION_TOKEN from .env
  sync_interval_seconds: 5
  batch_size: 100
  verify_ssl: false   # Recommended for Tailscale MagicDNS internal routing

ble:
  target_device_name: "WHOOP"
  auto_discover: true
  scan_timeout_seconds: 15.0
  reconnect_interval_seconds: 5.0
```

#### 2.3 Test the Collector
Run the runner batch script:
```powershell
.\run.bat
```
*(Or in PowerShell: `.\run.ps1`)*

You will see:
- Python dependencies verified/installed automatically.
- WHOOP discovered and connected over BLE.
- MTU 247 negotiated.
- Standard HR and battery notifications subscribed.
- Offload data transferred, persisted to local SQLite, and synced with `POST /api/v1/ingest/batches 200 OK`.

#### 2.4 Register as a Background Auto-Start Service
To make the collector run silently in the background on startup (no terminal window needed):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\install.ps1
```

This will:
- Lock configuration permissions to your user profile in `%LOCALAPPDATA%\NOOP`.
- Register `NOOP_HomeLab_Collector` in Windows Task Scheduler under interactive logon.
- Start the background task immediately via `pythonw.exe` with a system tray status icon.

You can now close your PowerShell/Command Prompt terminal windows!

---

### Step 3: Access the Web Dashboard

1. Open your browser on any phone, laptop, or desktop connected to your Tailnet:
   ```
   https://your-server.tailnet-name.ts.net
   ```
   *(Or locally: `http://<server-ip>:8080`)*

2. When the **Dashboard Authentication** modal appears, paste your `DASHBOARD_TOKEN` (from your server's `.env`).
   - The token is securely stored in your browser's `localStorage` and never leaves your private network.

3. Your dashboard will now display:
   - **Green LIVE Pill & Pulse**: Real-time heart rate streaming via WebSockets.
   - **Daily Recovery Gauge**: 0-100% composite score with HRV (RMSSD in ms) and resting HR.
   - **Day Strain Meter**: 0-21.0 logarithmic cardiovascular load (Banister TRIMP).
   - **Heart Rate Timeline**: Interactive 24-hour trace.
   - **Windows 11 Gateway**: Agent connection status, strap battery level, and sync telemetry.

---

### Useful Commands & Maintenance

#### Update Server to Latest Version
On your home server:
```bash
cd ~/noop-homelab
git pull
cd homelab
docker compose up -d --build
```

#### View Live API Logs
```bash
cd ~/noop-homelab/homelab
docker compose logs -f api
```

#### Check Windows Background Collector Task
In PowerShell on Windows:
```powershell
Get-ScheduledTask -TaskName "NOOP_HomeLab_Collector"
```

#### Stop / Uninstall Windows Background Collector
In PowerShell on Windows:
```powershell
cd Tools\windows-capture
.\uninstall.ps1
```

#### Database Backups
```bash
# Run manual backup
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh backups/noop_backup_<timestamp>.sql.gz
```
