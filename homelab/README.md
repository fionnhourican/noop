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
   - **React Dashboard**: Modern web interface with live stats, sleep staging, recovery trends, and system status.
   - **Tailscale Serve**: Secure remote access without exposing ports to the public internet.

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
