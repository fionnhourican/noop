# NOOP Home Lab — Hardware Validation Protocol (Gate A)

This document specifies the validation procedure and acceptance criteria for **Gate A**: physical discovery, Bluetooth Low Energy connection, GATT service identification, and live heart rate streaming on Windows 11.

Under project guidelines, **historical offload and server synchronization must not proceed until Gate A acceptance is verified on physical hardware**.

---

## 1. Prerequisites

Before attempting connection:

1. **Hardware Preparation**:
   - Ensure the WHOOP 4.0 strap has at least 30% battery charge.
   - **Crucial**: Turn off Bluetooth on your smartphone or force-quit the official WHOOP mobile app. WHOOP 4.0 supports only one active BLE central connection; if your phone is bonded and connected, the strap will not advertise to Windows.
   - Nudge or tap the strap to wake its BLE advertisement.
2. **Windows 11 Bluetooth**:
   - Ensure Windows 11 Bluetooth radio is enabled in *Settings > Bluetooth & devices*.
   - If Windows previously paired the WHOOP strap, confirm it is listed under *Devices*.

---

## 2. Verification Procedure

### Step 1: Broad BLE Discovery & GATT Enumeration
Run the collector scanner tool or discovery probe:

```powershell
cd Tools\windows-capture
python -m noop_agent.main --headless
```

**Expected Log Output**:
```
[INFO] Starting BLE scan (timeout=10.0s, target=ANY WHOOP 4.0)...
[INFO] Found WHOOP strap: WHOOP 4.0 (EB:12:34:56:78:9A)
[INFO] Connecting to WHOOP 4.0 (EB:12:34:56:78:9A)...
[INFO] Checking/requesting Windows OS-level pairing...
[INFO] Windows pairing result: True
[INFO] Successfully established BLE link to EB:12:34:56:78:9A
```

### Step 2: Characteristic & Notification Verification
The agent enumerates GATT services and subscribes to:
- Standard Heart Rate (`00002a37-0000-1000-8000-00805f9b34fb`)
- Standard Battery Level (`00002a19-0000-1000-8000-00805f9b34fb`)
- WHOOP Notify Channels (`61080003`, `61080004`, `61080005`)

**Expected Log Output**:
```
[INFO] Subscribed to Standard Heart Rate (00002a37-...)
[INFO] Subscribed to WHOOP 4 notify channel (61080003-...)
[INFO] Subscribed to WHOOP 4 notify channel (61080004-...)
[INFO] Subscribed to WHOOP 4 notify channel (61080005-...)
[INFO] Arming realtime sensor stream (SEND_R10_R11_REALTIME + TOGGLE_REALTIME_HR)...
```

### Step 3: Live Heart Rate & R-R Ingestion
Put on the strap or place a finger on the optical sensor. Once optical pulse lock is acquired (~30 seconds):

**Expected Telemetry**:
- System tray icon changes to 🟢 **Green** (`#22c55e`).
- Tooltip displays live pulse: `NOOP: Connected (72 bpm)`.
- Heart rate records are durably staged into `%LOCALAPPDATA%\NOOP\collector.sqlite`:
  ```sql
  SELECT record_type, timestamp_utc, value_json, sync_status 
  FROM collected_records 
  ORDER BY created_ms DESC LIMIT 5;
  ```

---

## 3. Acceptance Criteria Checklist (Gate A)

| Item | Requirement | Verification Method | Status |
|---|---|---|---|
| **A.1** | BLE Discovery | Strap discovered without requiring fixed MAC address | [ ] Pass |
| **A.2** | GATT Verification | Primary service `61080001` identified before interaction | [ ] Pass |
| **A.3** | Non-Destructive Handshake | Benign `CMD_GET_BATTERY_LEVEL` sent; zero DFU/wipe commands | [ ] Pass |
| **A.4** | Notification Subscriptions | Standard HR and 3 proprietary notify channels active | [ ] Pass |
| **A.5** | Real-time Heart Rate | Continuous live heart rate values received | [ ] Pass |
| **A.6** | R-R Intervals | R-R interval array unpacked and RMSSD calculated | [ ] Pass |
| **A.7** | Durable Local Persistence | Observations committed to local SQLite queue before sync | [ ] Pass |
| **A.8** | Safe Reconnection | Automatic reconnect on BLE drop with exponential backoff | [ ] Pass |

---

## 4. Troubleshooting

1. **Strap not advertising**:
   - Double-check phone Bluetooth is disabled.
   - Place strap on charger for 5 seconds to wake it, then remove.
2. **Windows WinRT pairing prompt**:
   - If Windows shows a toast notification stating "Pair with WHOOP 4.0", click **Allow**. WHOOP 4.0 uses BLE "Just Works" pairing.
3. **Bluetooth supervision timeout**:
   - Ensure the keepalive task is active (runs every 15s) re-issuing `CMD_TOGGLE_REALTIME_HR`.
