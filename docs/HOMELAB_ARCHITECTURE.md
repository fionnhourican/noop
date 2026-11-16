# NOOP Home Lab — System Architecture & Design

## 1. System Vision

NOOP Home Lab extends the NOOP offline-first philosophy to a continuous, self-hosted WHOOP 4.0 monitoring platform. It bridges a personal Windows 11 laptop (acting as a BLE gateway) to a Linux home server (providing persistent PostgreSQL storage, ported NOOP analytics, and an interactive web dashboard) via an encrypted Tailscale network.

---

## 2. Component Topology

```
+-------------------------------------------------------------------------------+
|                                  WHOOP 4.0                                    |
+-------------------------------------------------------------------------------+
                                       |
                   Bluetooth Low Energy (GATT / WinRT)
                                       v
+-------------------------------------------------------------------------------+
|                       Windows 11 Background Agent                             |
|                                                                               |
|  [Agent Supervisor] (Single Instance Mutex: Global\NOOP_HomeLab_Collector)    |
|       |                                                                       |
|       +--> [System Tray UI] (Pystray / Decoupled from BLE)                    |
|       |                                                                       |
|       +--> [BLE Connection Manager] (Bleak / WinRT)                           |
|       |         |                                                             |
|       |         +--> [Live Pipeline]                                          |
|       |         |    - Real-time HR (00002a37-...)                            |
|       |         |    - Battery Level & Events (Packet 48)                     |
|       |         |    - Bounded Queue -> SQLite Flush                          |
|       |         |                                                             |
|       |         +--> [Historical Offload Pipeline]                            |
|       |              - Command 22 Trigger                                     |
|       |              - Chunk Stream & Reassembly (Packet 47)                  |
|       |              - Persist-before-ACK (Command 23)                        |
|       |                                                                       |
|       +--> [Local SQLite Queue] (%LOCALAPPDATA%\NOOP\collector.sqlite)        |
|       |    - WAL Journal Mode, synchronous=FULL                               |
|       |    - Tables: raw_frames, source_records, queue, sync_state            |
|       |                                                                       |
|       +--> [HTTPX Sync Worker]                                                |
|            - POST /api/v1/ingest/batches                                      |
|            - Exponential Backoff + Jitter (HTTP 429 / 5xx / Network offline)  |
+-------------------------------------------------------------------------------+
                                       |
                       HTTPS over Tailscale Encrypted Mesh
                                       v
+-------------------------------------------------------------------------------+
|                        Linux Home Server (Docker)                             |
|                                                                               |
|  Tailscale Serve (HTTPS)                                                      |
|       |                                                                       |
|       v                                                                       |
|  Docker Compose (127.0.0.1:8080:80)                                           |
|       |                                                                       |
|       +--> [Nginx Reverse Proxy / React Frontend]                             |
|       |    - Dashboard UI (Recharts / Vite / TypeScript)                      |
|       |    - Reverse proxies /api/v1 -> api:8000                              |
|       |    - Reverse proxies /ws -> api:8000                                  |
|       |                                                                       |
|       +--> [FastAPI Application Server]                                       |
|       |    - Ingestion API (Bearer Ingestion Token, Idempotent)               |
|       |    - Domain Endpoints (Heart rate, Sleep, Recovery, Strain, Workouts) |
|       |    - Analytics Engine (HRV RMSSD, Z-score Recovery, TRIMP Strain)     |
|       |    - WebSocket Hub (/api/v1/live)                                     |
|       |                                                                       |
|       +--> [PostgreSQL 17 Database]                                           |
|            - Persistent Volume (noop_postgres_data)                           |
|            - Automated Daily pg_dump Backup Script                            |
+-------------------------------------------------------------------------------+
```

---

## 3. Key Design Decisions

1. **Independent Collection Pipelines**:
   - Live heart rate (`00002a37`) and real-time events must never be blocked by large historical offloads.
   - Live data flushes to local SQLite in real time while historical chunks commit independently.
2. **Persist-Before-ACK**:
   - The collector writes and commits historical chunks to durable SQLite before acknowledging (`CMD_HISTORICAL_DATA_RESULT`) to the strap. This prevents data loss if a connection drops mid-offload.
3. **Data Provenance**:
   - All parsed metrics link back to their originating `source_record_id` and immutable `raw_frame_id`, carrying `protocol_version`, `decoder_version`, and `data_origin` (`live` vs `historical`).
4. **Offline Resilience**:
   - The Windows agent operates completely offline if the home server or Tailscale connection is down.
   - When connection is restored, pending records sync automatically in batches with idempotency guarantees.
5. **Security Boundaries**:
   - Ingestion credentials (Windows agent) and dashboard access (browser) use separate authentication tokens.
   - Database and application ports are never exposed to the public internet; remote access is secured exclusively via Tailscale.
