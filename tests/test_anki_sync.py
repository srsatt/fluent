#!/usr/bin/env python3
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_update_db import make_fixtures

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "anki-sync.py"


class AnkiSyncTest(unittest.TestCase):
    def test_export_tsv_contains_fluent_id_and_card_fields(self):
        with tempfile.TemporaryDirectory(prefix="fluent-anki-") as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            make_fixtures(data_dir)
            output = root / "anki.tsv"

            proc = subprocess.run(
                [
                    "python3", str(SCRIPT), "export-tsv",
                    "--data-dir", str(data_dir),
                    "--output", str(output),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            text = output.read_text(encoding="utf-8")
            self.assertIn("#separator:tab", text)
            self.assertIn("#columns:Front\tBack\tContext\tFluentId\tTags", text)
            self.assertIn("vocab_dag", text)
            self.assertIn("fluent_type::vocabulary", text)

    def test_push_dry_run_does_not_need_anki(self):
        with tempfile.TemporaryDirectory(prefix="fluent-anki-") as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            make_fixtures(data_dir)

            proc = subprocess.run(
                [
                    "python3", str(SCRIPT), "push",
                    "--data-dir", str(data_dir),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn('"would_push": 1', proc.stdout)


if __name__ == "__main__":
    unittest.main()
