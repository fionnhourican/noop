# NOOP Home Lab — API Specification

The NOOP Home Lab API is a FastAPI-powered REST and WebSocket service providing authenticated batch ingestion for the Windows BLE collector, domain data retrieval, and real-time streaming for web dashboards.

- **Base URL**: `/api/v1`
- **Interactive Documentation**: `/api/v1/docs` (Swagger UI) / `/api/v1/redoc` (ReDoc)
- **OpenAPI Schema**: `/api/v1/openapi.json`

---

## 1. Authentication

The API uses HTTP Bearer token authentication with constant-time comparison (`secrets.compare_digest`) to protect against timing attacks.

Separate credentials are required:

| Role | Header | Config Key | Purpose |
|---|---|---|---|
| **Collector Ingestion** | `Authorization: Bearer <INGESTION_TOKEN>` | `INGESTION_TOKEN` | Ingestion from Windows 11 collector |
| **Browser Dashboard** | `Authorization: Bearer <DASHBOARD_TOKEN>` | `DASHBOARD_TOKEN` | Dashboard queries and data access |

### Error Responses
- `401 Unauthorized`: Missing or malformed `Authorization` header.
- `403 Forbidden`: Token mismatch or invalid signature.

---

## 2. Endpoints Overview

| Method | Path | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/health` | Service health status and timestamp | None |
| `POST` | `/api/v1/ingest/batches` | Ingest observation batch (Idempotent) | Ingestion Token |
| `GET` | `/api/v1/devices` | List registered WHOOP bands | Dashboard Token |
| `GET` | `/api/v1/heart-rate` | Query historical heart rate samples | Dashboard Token |
| `GET` | `/api/v1/sleep` | Query sleep sessions and stages | Dashboard Token |
| `GET` | `/api/v1/recovery` | Query daily recovery scores | Dashboard Token |
| `GET` | `/api/v1/strain` | Query daily strain scores | Dashboard Token |
| `GET` | `/api/v1/workouts` | Query workout sessions | Dashboard Token |
| `GET` | `/api/v1/collector/status` | Get latest Windows agent telemetry | Dashboard Token |
| `POST` | `/api/v1/collector/status` | Update agent status heartbeat | Ingestion Token |
| `GET` | `/api/v1/dashboard/summary` | Consolidated summary for overview card | Dashboard Token |
| `WS` | `/ws/live` | WebSocket stream for live heart rate | None (Tailnet private) |

---

## 3. Ingestion Endpoint

### `POST /api/v1/ingest/batches`

Submit a versioned batch of collected observations.

#### Request Headers
```http
Content-Type: application/json
Authorization: Bearer <INGESTION_TOKEN>
```

#### Request Body
```json
{
  "schema_version": 1,
  "device_id": "whoop-4-local",
  "batch_id": "b8f5a1e2-9b2d-4c3e-8f1a-2e3d4c5b6a7b",
  "records": [
    {
      "record_id": "7a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
      "type": "heart_rate",
      "timestamp": "2026-11-16T18:30:00Z",
      "reception_timestamp": "2026-11-16T18:30:00.120Z",
      "data_origin": "live",
      "validation_status": "valid",
      "protocol_version": 4,
      "decoder_version": "1.0.0",
      "value": 72,
      "unit": "bpm",
      "source": "whoop_ble",
      "raw_frame_hex": "aa070007280000480023456789",
      "char_uuid": "00002a37-0000-1000-8000-00805f9b34fb",
      "inner_type": 40
    },
    {
      "record_id": "8b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
      "type": "biometric",
      "timestamp": "2026-11-16T18:30:00Z",
      "data_origin": "historical",
      "validation_status": "valid",
      "protocol_version": 4,
      "decoder_version": "1.0.0",
      "metadata": {
        "rr_count": 1,
        "rr_mean_ms": 833.0,
        "rmssd": 45.2,
        "gravity_x": -0.05,
        "gravity_y": 0.12,
        "gravity_z": 0.98,
        "spo2_red": 32450,
        "spo2_ir": 41200,
        "skin_temp_raw": 826,
        "skin_temp_c": 33.4,
        "record_version": 24
      }
    }
  ]
}
```

#### Response (200 OK)
```json
{
  "status": "success",
  "batch_id": "b8f5a1e2-9b2d-4c3e-8f1a-2e3d4c5b6a7b",
  "accepted": 2,
  "duplicates": 0,
  "rejected": 0,
  "message": "Batch processed: 2 accepted, 0 duplicate(s), 0 rejected"
}
```

---

## 4. Query Endpoints

### `GET /api/v1/heart-rate`
Query historical per-second heart rates.
- `device_id`: Device identifier filter.
- `start_time`: ISO 8601 UTC timestamp.
- `end_time`: ISO 8601 UTC timestamp.
- `limit`: Number of samples (default 500, max 5000).

### `GET /api/v1/dashboard/summary`
Unified overview statistics:
```json
{
  "latest_heart_rate": {
    "timestamp": "2026-11-16T19:00:00Z",
    "bpm": 64,
    "source": "whoop_ble"
  },
  "latest_recovery": {
    "date": "2026-11-16",
    "recovery_score": 78.5,
    "hrv_rmssd": 68.2,
    "resting_heart_rate": 54.0,
    "respiratory_rate": 14.2,
    "skin_temp_deviation": -0.1,
    "algorithm_version": "noop_recovery_v1"
  },
  "latest_strain": {
    "date": "2026-11-16",
    "strain_score": 12.4,
    "average_hr": 78.0,
    "max_hr": 158,
    "kilojoules": 1850.0,
    "algorithm_version": "noop_strain_banister_v1"
  },
  "collector_status": {
    "device_id": "whoop-4-local",
    "last_seen": "2026-11-16T19:05:00Z",
    "connection_state": "connected",
    "battery_percentage": 84.0,
    "battery_millivolts": 4120,
    "is_charging": false,
    "queued_records": 0,
    "agent_version": "1.0.0"
  }
}
```
