# NOOP Home Lab — Server Deployment Guide

This guide details setting up the Linux home server components for NOOP Home Lab using Docker Compose and Tailscale Serve.

---

## Prerequisites

- Linux home server (Ubuntu 22.04+, Debian 12+, Arch, etc.)
- Docker Engine 24.0+ and Docker Compose v2.20+
- Tailscale installed and authenticated on the Linux host
- No Bluetooth hardware is needed on the server (the Windows laptop serves as the BLE gateway)

---

## 1. Environment Configuration

Clone your private fork of NOOP and navigate to `homelab/`:

```bash
cd noop/homelab
cp .env.example .env
```

Generate secure random secrets:

```bash
# Generate database password
openssl rand -hex 24

# Generate 32+ character ingestion token for the Windows agent
openssl rand -base64 32

# Generate dashboard session token
openssl rand -base64 32
```

Edit `.env`:

```env
POSTGRES_USER=noop
POSTGRES_PASSWORD=<generated_db_password>
POSTGRES_DB=noop_homelab
INGESTION_TOKEN=<generated_ingestion_token>
DASHBOARD_TOKEN=<generated_dashboard_token>
PORT=8080
```

> **Security Note:** Never commit `.env` to git. Keep `INGESTION_TOKEN` separate from `DASHBOARD_TOKEN`.

---

## 2. Starting the Stack

Build and start the containers in detached mode:

```bash
docker compose up -d --build
```

Check container status and health:

```bash
docker compose ps
```

Expected output:
```
NAME            IMAGE               COMMAND                  SERVICE    STATUS
noop_postgres   postgres:17-alpine  "docker-entrypoint.s…"   postgres   Up (healthy)
noop_api        homelab-api         "uvicorn app.main:ap…"   api        Up
noop_frontend   homelab-frontend    "/docker-entrypoint.…"   frontend   Up (127.0.0.1:8080->80/tcp)
```

Test the internal health endpoint:

```bash
curl -i http://127.0.0.1:8080/api/v1/health
```

Expected response:
```json
{"status":"healthy","service":"NOOP Home Lab API","version":"1.0.0","environment":"production","timestamp":"..."}
```

---

## 3. Remote Access via Tailscale Serve

Tailscale runs directly on the Linux host. The Docker stack binds strictly to `127.0.0.1:8080` to prevent unintended exposure to the local network.

Expose the dashboard and ingestion API over your Tailnet:

```bash
sudo tailscale serve --bg http://127.0.0.1:8080
```

To check the assigned MagicDNS HTTPS URL:

```bash
tailscale serve status
```

Output will display your endpoint URL, typically:
```
https://your-server-name.your-tailnet.ts.net
```

Use this URL on the Windows 11 collector (`https://your-server-name.your-tailnet.ts.net/api/v1`) and in your web browser.

---

## 4. Database Backups and Retention

### Automated Daily Backup

Add a cron job to run `backup.sh` every day at 03:00 UTC:

```bash
crontab -e
```

Add the following line:

```cron
0 3 * * * /path/to/noop/homelab/scripts/backup.sh >> /var/log/noop_backup.log 2>&1
```

### Manual Backup

```bash
./scripts/backup.sh
```

Backups are saved to `homelab/backups/noop_backup_<timestamp>.sql.gz`. Files older than 30 days are purged automatically.

### Database Restoration

To restore from a backup:

```bash
./scripts/restore.sh backups/noop_backup_20261116_120000Z.sql.gz
```

Type `yes` when prompted to confirm the restoration.
