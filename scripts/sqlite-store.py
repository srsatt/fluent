#!/usr/bin/env python3
"""
Export/import Fluent learner stores with SQLite.

SQL is the default runtime backend. This utility is still useful for explicit
exports, restores, and JSON compatibility workflows.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import data_dir, force_utf8_io, sqlite_db_path  # noqa: E402
from fluent_storage import (  # noqa: E402
    load_json_documents,
    load_sqlite_documents,
    save_json_documents,
    save_sqlite_documents,
)

force_utf8_io()


def export_to_sqlite(db_path: Path, source_dir: Path) -> None:
    docs, missing = load_json_documents(source_dir)
    if missing:
        raise SystemExit(f"Missing Fluent JSON files: {', '.join(missing)}")
    save_sqlite_documents(docs, db_path)
    print(f"[Fluent] Exported {len(docs)} stores to {db_path}")


def import_to_json(db_path: Path, output_dir: Path) -> None:
    docs, missing = load_sqlite_documents(db_path)
    if missing:
        raise SystemExit(f"SQLite store is missing documents: {', '.join(missing)}")
    save_json_documents(docs, output_dir)
    print(f"[Fluent] Restored {len(docs)} stores to {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="Export JSON stores to SQLite")
    exp.add_argument("--db", type=Path, default=None, help="SQLite output path")
    exp.add_argument("--data-dir", type=Path, default=None, help="Fluent JSON data dir")

    imp = sub.add_parser("import", help="Restore JSON stores from SQLite")
    imp.add_argument("--db", type=Path, default=None, help="SQLite source path")
    imp.add_argument("--output-dir", type=Path, default=None, help="JSON output directory")

    args = parser.parse_args()
    if args.command == "export":
        source = args.data_dir.resolve() if args.data_dir else data_dir()
        db_path = args.db.resolve() if args.db else sqlite_db_path()
        export_to_sqlite(db_path, source)
    elif args.command == "import":
        db_path = args.db.resolve() if args.db else sqlite_db_path()
        output = args.output_dir.resolve() if args.output_dir else data_dir()
        import_to_json(db_path, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
