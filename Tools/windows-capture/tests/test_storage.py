"""Tests for local SQLite database initialization and WAL configuration."""

import tempfile
from pathlib import Path
from noop_agent.storage.local_db import LocalDatabase


def test_db_initialization_and_wal():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_collector.sqlite"
        db = LocalDatabase(db_path)
        conn = db.get_connection()

        # Verify tables exist
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "devices" in tables
        assert "raw_frames" in tables
        assert "collected_records" in tables
        assert "upload_batches" in tables
        assert "sync_state" in tables

        # Verify WAL mode
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"

        db.close()
