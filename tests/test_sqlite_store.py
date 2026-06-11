#!/usr/bin/env python3
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_update_db import make_fixtures

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "sqlite-store.py"


class SqliteStoreTest(unittest.TestCase):
    def test_export_and_import_round_trip(self):
        with tempfile.TemporaryDirectory(prefix="fluent-sqlite-") as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            out_dir = root / "restored"
            data_dir.mkdir()
            make_fixtures(data_dir)

            db_path = root / "fluent.sqlite"
            proc = subprocess.run(
                [
                    "python3", str(SCRIPT), "export",
                    "--data-dir", str(data_dir),
                    "--db", str(db_path),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(db_path.exists())

            with sqlite3.connect(db_path) as con:
                docs = con.execute("SELECT count(*) FROM documents").fetchone()[0]
                items = con.execute("SELECT count(*) FROM review_items").fetchone()[0]
                sessions = con.execute("SELECT count(*) FROM sessions").fetchone()[0]
            self.assertEqual(docs, 6)
            self.assertEqual(items, 1)
            self.assertEqual(sessions, 1)

            proc = subprocess.run(
                [
                    "python3", str(SCRIPT), "import",
                    "--db", str(db_path),
                    "--output-dir", str(out_dir),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            restored = json.loads((out_dir / "learner-profile.json").read_text())
            self.assertEqual(restored["learner"]["name"], "Test")


if __name__ == "__main__":
    unittest.main()
