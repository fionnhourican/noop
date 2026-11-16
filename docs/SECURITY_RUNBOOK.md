# NOOP Home Lab — Security & Token Rotation Runbook

This document details the security posture, network isolation boundaries, and credential rotation procedures for the NOOP Home Lab platform.

---

## 1. Security Architecture & Boundary Verification

NOOP Home Lab enforces strict isolation across all operational planes:

```
+-------------------------------------------------------------------------+
| Plane 1: Bluetooth Low Energy (Interactive User Session on Windows)     |
|   - Bleak GATT communication restricted to paired WHOOP 4.0 UUIDs.      |
|   - Reversible commands only; zero firmware/DFU writes.                 |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| Plane 2: Windows Ingestion Gateway (Restricted Bearer Token)             |
|   - Bearer token stored in Windows Credential Manager.                  |
|   - Local SQLite queue restricted via Windows DACL (current user only). |
|   - Transmits to Home Lab strictly via HTTPS over Tailscale.            |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| Plane 3: Private Tailscale Network (Mutual WireGuard Mesh)              |
|   - Zero public internet port forwarding.                               |
|   - Tailscale Serve terminates TLS with automatic Let's Encrypt certs.  |
|   - Host loopback binding strictly to 127.0.0.1:8080.                   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| Plane 4: Linux Home Server Internal Docker Network                      |
|   - PostgreSQL (5432) has NO published host ports.                      |
|   - FastAPI (8000) has NO published host ports.                         |
|   - Timing attack protection via constant-time secrets.compare_digest.  |
+-------------------------------------------------------------------------+
```

### Verification Checklist:
1. **Verify No Exposed Database Ports**:
   ```bash
   sudo ss -tulpn | grep 5432
   ```
   *Expected output*: Empty. PostgreSQL must not listen on any host interface.
2. **Verify Nginx Host Binding**:
   ```bash
   sudo ss -tulpn | grep 8080
   ```
   *Expected output*: `127.0.0.1:8080` (loopback only). Must never show `0.0.0.0:8080` or `:::8080`.
3. **Verify Tailscale ACLs**:
   In your Tailscale admin console, verify that only authorized devices on your Tailnet can reach the home server's Tailscale IP.

---

## 2. Credential Rotation Procedures

Three separate secrets protect the system:
1. `INGESTION_TOKEN`: Authenticates the Windows agent to `POST /api/v1/ingest/batches`.
2. `DASHBOARD_TOKEN`: Authenticates browser sessions to query API endpoints.
3. `POSTGRES_PASSWORD`: Internal database connection password.

---

### Procedure A: Rotating the Windows Ingestion Token

*Objective*: Rotate `INGESTION_TOKEN` without dropping queued records on Windows.

1. **Generate New Secret Token**:
   ```bash
   openssl rand -hex 32
   ```
2. **Update Home Server `.env`**:
   Edit `homelab/.env` and update `INGESTION_TOKEN`:
   ```ini
   INGESTION_TOKEN=new_generated_token_value_here
   ```
3. **Restart API Service**:
   ```bash
   cd homelab
   docker compose up -d api
   ```
4. **Update Windows Credential Manager**:
   Open PowerShell on your Windows 11 laptop:
   ```powershell
   cmdkey /generic:"NOOP_HomeLab_Ingestion" /user:"collector" /pass:"new_generated_token_value_here"
   ```
5. **Verify Synchronization**:
   Right-click the NOOP system tray icon and click **Synchronise Now**.
   Inspect `%LOCALAPPDATA%\NOOP\logs\collector.log` to confirm batches are accepted (HTTP 200 OK).

---

### Procedure B: Rotating the Dashboard Access Token

*Objective*: Rotate `DASHBOARD_TOKEN` to revoke existing browser sessions.

1. **Generate New Secret Token**:
   ```bash
   openssl rand -hex 24
   ```
2. **Update Home Server `.env`**:
   Edit `homelab/.env` and update `DASHBOARD_TOKEN`:
   ```ini
   DASHBOARD_TOKEN=new_dashboard_token_value_here
   ```
3. **Restart API Service**:
   ```bash
   cd homelab
   docker compose up -d api
   ```
4. **Re-authenticate Browser Dashboard**:
   - Open your dashboard in browser (`https://your-server.your-tailnet.ts.net`).
   - The dashboard will detect HTTP 401 and present the **Dashboard Authentication** dialog.
   - Enter the new token and click **Save & Connect**.

---

### Procedure C: Rotating PostgreSQL Password

*Objective*: Update internal database credentials with zero data loss.

1. **Generate New Database Password**:
   ```bash
   openssl rand -hex 16
   ```
2. **Alter PostgreSQL User Password**:
   ```bash
   docker compose exec postgres psql -U noop -d noop_homelab -c "ALTER USER noop WITH PASSWORD 'new_password_here';"
   ```
3. **Update Home Server `.env`**:
   Edit `homelab/.env`:
   ```ini
   POSTGRES_PASSWORD=new_password_here
   ```
4. **Restart API Service**:
   ```bash
   docker compose up -d api
   ```
5. **Verify API Database Connectivity**:
   ```bash
   curl -f http://127.0.0.1:8080/api/v1/health
   ```
   *Expected response*: `{"status":"healthy","database":"connected",...}`
