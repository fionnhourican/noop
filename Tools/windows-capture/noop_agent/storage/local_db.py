"""Durable local SQLite persistence in WAL mode."""

import os
import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA = """
-- Registered or discovered devices
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL UNIQUE,
    name TEXT,
    model TEXT DEFAULT 'whoop4',
    created_ms INTEGER NOT NULL
);

-- Immutable raw BLE frames
CREATE TABLE IF NOT EXISTS raw_frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    recv_ms INTEGER NOT NULL,
    char_uuid TEXT NOT NULL,
    inner_type INTEGER,
    frame_hex TEXT NOT NULL,
    UNIQUE(device_id, frame_hex)
);
CREATE INDEX IF NOT EXISTS idx_raw_frames_dev_recv ON raw_frames(device_id, recv_ms);

-- Durable queue of parsed observation records
CREATE TABLE IF NOT EXISTS collected_records (
    record_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    reception_utc TEXT NOT NULL,
    raw_frame_id INTEGER,
    protocol_version INTEGER DEFAULT 4,
    decoder_version TEXT DEFAULT '1.0.0',
    data_origin TEXT DEFAULT 'live',
    validation_status TEXT DEFAULT 'valid',
    value_json TEXT,
    unit TEXT,
    source TEXT,
    metadata_json TEXT,
    sync_status TEXT DEFAULT 'pending',  -- 'pending', 'in_flight', 'synced'
    batch_id TEXT,
    created_ms INTEGER NOT NULL,
    FOREIGN KEY(raw_frame_id) REFERENCES raw_frames(id)
);
CREATE INDEX IF NOT EXISTS idx_records_status ON collected_records(sync_status);
CREATE INDEX IF NOT EXISTS idx_records_batch ON collected_records(batch_id);
CREATE INDEX IF NOT EXISTS idx_records_dev_time ON collected_records(device_id, timestamp_utc);

-- Historical upload batch tracking
CREATE TABLE IF NOT EXISTS upload_batches (\n    batch_id TEXT PRIMARY KEY,
    created_ms INTEGER NOT NULL,
    records_count INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',       -- 'pending', 'sent', 'acknowledged', 'failed'
    response_json TEXT,
    acknowledged_ms INTEGER
);

-- Key-value persistent state (cursors, trim marks)
CREATE TABLE IF NOT EXISTS sync_state (
    device_id TEXT NOT NULL,
    k TEXT NOT NULL,
    v TEXT NOT NULL,
    PRIMARY KEY(device_id, k)
);
"""


class LocalDatabase:
    """Manages SQLite connection with WAL journal mode and immediate transactions."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database, apply schema, and configure WAL mode."""
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
        )
        self.conn.row_factory = sqlite3.Row
        with self.conn:
            self.conn.executescript(SCHEMA)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=FULL")

    def get_connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self._init_db()
        return self.conn

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None
