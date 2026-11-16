# NOOP Home Lab — Self-Hosted WHOOP 4.0 Platform

A self-hosted, offline-first companion system for the WHOOP 4.0 fitness band.

## Architecture Overview

```
WHOOP 4.0 (BLE)  --->  Windows 11 Collector Agent  --->  Linux Home Server (Docker + Tailscale)
```

1. **Windows 11 Collector Agent** (`Tools/windows-capture/`):
   - Direct Bluetooth LE communication using Bleak.
   - Separate asynchronous pipelines: Live Heart Rate (`2a37`) & Historical Offload (`SEND_HISTORICAL_DATA`).
   - Durable local SQLite storage (`%LOCALAPPDATA%\NOOP\collector.sqlite`) in WAL mode.
   - Background system tray application with single-instance mutex and status indicators.
   - Automatic retries with exponential backoff and jitter.

2. **Linux Home Server** (`homelab/`):
   - **Docker Compose**: Orchestrates PostgreSQL 17, FastAPI backend, and Nginx frontend.
   - **PostgreSQL 17**: Relational storage for immutable raw frames, source records, and normalized biometric samples.
   - **FastAPI Backend**: Authenticated batch ingestion endpoint, ported NOOP analytics (RMSSD, z-score recovery, TRIMP strain), and WebSockets for live streaming.
   - **React Dashboard**: Modern web interface built with React 18, Vite, TypeScript, and Tailwind CSS. Features real-time WebSocket heart rate pulse, daily recovery gauge (0-100%), logarithmic day strain meter (0-21.0), sleep architecture breakdown, workouts list, and Windows collector telemetry.
   - **Tailscale Serve**: Secure remote access without exposing ports to the public internet.

## Web Dashboard Features

The web dashboard is served on port `8080` (or your Tailscale HTTPS URL) and features a dark, high-contrast aesthetic modeled after NOOP's palette:

- **Today's Overview**:
  - **Daily Recovery Score**: Circular progress gauge (0-100%) with Green (≥67%), Yellow (34-66%), and Red (≤33%) zones, HRV (RMSSD in ms), and resting heart rate (RHR).
  - **Day Strain Meter**: Cardiovascular load on a 0-21.0 scale with smooth gradient progress, average HR, max HR, and energy expenditure.
  - **Live Heart Rate Card**: Real-time heart rate pulse animation synced to current BPM via WebSocket (`/ws/live`), battery indicator, and a rolling 30-second SVG sparkline.
  - **Sleep Architecture**: Total sleep time, bedtime/wake times, sleep efficiency %, and segmented stage breakdown (Deep, REM, Light, Awake).
  - **Heart Rate Timeline**: Interactive SVG time-series chart showing 24-hour heart rate trends with min/max bounds.
  - **Recorded Workouts**: Chronological activity feed with sport type, duration, average HR, and workout strain score.
  - **Windows 11 Gateway Status**: Live telemetry showing agent connection state, target strap address, battery level, local queue backlog count, and last sync timestamp.
- **Dedicated Tabs**: Deep-dive views for Recovery, Day Strain, Sleep Architecture, Activities, and Hardware Telemetry.
- **Tailscale Access & Authentication**: Session security via Bearer token with an in-app settings modal. Accessible from phones, tablets, or remote browsers on your Tailnet.

## Getting Started

### 1. Server Setup

Navigate to `homelab/` on your Linux server:

```bash
cd homelab
cp .env.example .env
# Edit .env and set strong secrets for POSTGRES_PASSWORD, INGESTION_TOKEN, and DASHBOARD_TOKEN
```

Start the containers:

```bash
docker compose up -d
```

Verify that the health check passes:

```bash
curl -f http://127.0.0.1:8080/api/v1/health
```

Expose securely via Tailscale Serve:

```bash
sudo tailscale serve --bg http://127.0.0.1:8080
```

### 2. Windows 11 Collector Setup

Follow the instructions in [`docs/WINDOWS_SETUP.md`](../docs/WINDOWS_SETUP.md).

### 3. Backups

Run manual or scheduled database backups:

```bash
./scripts/backup.sh
```

To restore from a backup:

```bash
./scripts/restore.sh backups/noop_backup_<timestamp>.sql.gz
```
