"""Tests for local SQLite database initialization and WAL configuration."""

import tempfile
import unittest
from pathlib import Path

from noop_agent.storage.local_db import LocalDatabase


class TestStorage(unittest.TestCase):

    def test_db_initialization_and_wal(self):
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
            self.assertIn("devices", tables)
            self.assertIn("raw_frames", tables)
            self.assertIn("collected_records", tables)
            self.assertIn("upload_batches", tables)
            self.assertIn("sync_state", tables)

            # Verify WAL mode
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

            db.close()


if __name__ == "__main__":
    unittest.main()
