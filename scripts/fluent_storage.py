"""
Storage adapter for Fluent learner stores.

The helper scripts call this module instead of knowing whether the runtime
source is SQLite or JSON. SQL is the default backend; JSON remains available
with FLUENT_DB=json or db=json in .env.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from fluent_paths import data_dir, db_backend, sqlite_db_path

FILES = {
    "learner_profile": "learner-profile.json",
    "progress_db": "progress-db.json",
    "mistakes_db": "mistakes-db.json",
    "mastery_db": "mastery-db.json",
    "spaced_repetition": "spaced-repetition.json",
    "session_log": "session-log.json",
}


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp_path), str(path))


def load_json_documents(source_dir: Path | None = None) -> tuple[dict[str, dict], list[str]]:
    source = source_dir or data_dir()
    docs: dict[str, dict] = {}
    missing: list[str] = []
    for key, filename in FILES.items():
        doc = read_json(source / filename)
        if doc is None:
            docs[key] = {}
            missing.append(str(source / filename))
        else:
            docs[key] = doc
    return docs, missing


def save_json_documents(docs: dict[str, dict], target_dir: Path | None = None) -> None:
    target = target_dir or data_dir()
    target.mkdir(parents=True, exist_ok=True)
    for key, filename in FILES.items():
        save_json(target / filename, docs.get(key, {}))


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or sqlite_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA foreign_keys = ON")
    return con


def create_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
          name TEXT PRIMARY KEY,
          json_text TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS review_items (
          item_id TEXT PRIMARY KEY,
          item_type TEXT,
          content TEXT,
          answer TEXT,
          due_date TEXT,
          mastery_level INTEGER,
          priority TEXT,
          json_text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
          session_id TEXT PRIMARY KEY,
          date TEXT,
          command_used TEXT,
          accuracy REAL,
          json_text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS error_patterns (
          pattern_id TEXT PRIMARY KEY,
          category TEXT,
          severity TEXT,
          frequency INTEGER,
          mastery_level INTEGER,
          json_text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS metadata (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        """
    )


def sqlite_has_documents(db_path: Path | None = None) -> bool:
    path = db_path or sqlite_db_path()
    if not path.exists():
        return False
    try:
        with sqlite3.connect(str(path)) as con:
            row = con.execute("SELECT count(*) FROM documents").fetchone()
    except sqlite3.Error:
        return False
    return bool(row and row[0] >= len(FILES))


def load_sqlite_documents(db_path: Path | None = None) -> tuple[dict[str, dict], list[str]]:
    path = db_path or sqlite_db_path()
    if not path.exists():
        return {}, [str(path)]
    with sqlite3.connect(str(path)) as con:
        create_schema(con)
        rows = con.execute("SELECT name, json_text FROM documents").fetchall()
    docs = {name: json.loads(text) for name, text in rows}
    missing = [name for name in FILES if name not in docs]
    for key in missing:
        docs[key] = {}
    return docs, missing


def save_sqlite_documents(docs: dict[str, dict], db_path: Path | None = None) -> None:
    path = db_path or sqlite_db_path()
    exported_at = datetime.now().isoformat(timespec="seconds")
    with connect(path) as con:
        create_schema(con)
        for table in ("documents", "review_items", "sessions", "error_patterns", "metadata"):
            con.execute(f"DELETE FROM {table}")

        for name in FILES:
            doc = docs.get(name, {})
            con.execute(
                "INSERT INTO documents(name, json_text, updated_at) VALUES (?, ?, ?)",
                (name, json.dumps(doc, ensure_ascii=False), exported_at),
            )

        sr = docs.get("spaced_repetition", {})
        for item_id, item in sr.get("items", {}).items():
            con.execute(
                """
                INSERT INTO review_items(
                  item_id, item_type, content, answer, due_date,
                  mastery_level, priority, json_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    item.get("type", ""),
                    item.get("content", ""),
                    item.get("answer", ""),
                    item.get("due_date", ""),
                    item.get("mastery_level", 0),
                    item.get("priority", ""),
                    json.dumps(item, ensure_ascii=False),
                ),
            )

        log = docs.get("session_log", {})
        for session in log.get("sessions", []):
            sid = session.get("session_id") or session.get("id")
            if not sid:
                continue
            con.execute(
                """
                INSERT INTO sessions(session_id, date, command_used, accuracy, json_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    session.get("date", ""),
                    session.get("command_used", ""),
                    session.get("accuracy", 0.0),
                    json.dumps(session, ensure_ascii=False),
                ),
            )

        mistakes = docs.get("mistakes_db", {})
        for pattern_id, pattern in mistakes.get("error_patterns", {}).items():
            con.execute(
                """
                INSERT INTO error_patterns(
                  pattern_id, category, severity, frequency, mastery_level, json_text
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    pattern_id,
                    pattern.get("category", ""),
                    pattern.get("severity", ""),
                    pattern.get("frequency", 0),
                    pattern.get("mastery_level", 0),
                    json.dumps(pattern, ensure_ascii=False),
                ),
            )

        con.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("updated_at", exported_at))
        con.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("backend", "sql"))


def load_documents() -> tuple[dict[str, dict], list[str], str]:
    """Load docs from configured backend. SQL bootstraps from JSON if needed."""
    backend = db_backend()
    if backend == "json":
        docs, missing = load_json_documents()
        return docs, missing, backend

    if sqlite_has_documents():
        docs, missing = load_sqlite_documents()
        return docs, missing, backend

    docs, missing = load_json_documents()
    if not missing:
        save_sqlite_documents(docs)
    return docs, missing, backend


def save_documents(docs: dict[str, dict], mirror_json: bool = True) -> str:
    """Save docs to configured backend. SQL mode keeps JSON mirrors by default."""
    backend = db_backend()
    if backend == "json":
        save_json_documents(docs)
        return backend
    save_sqlite_documents(docs)
    if mirror_json:
        save_json_documents(docs)
    return backend


def storage_files_for_backup() -> list[Path]:
    files = [path for path in data_dir().glob("*.json") if path.is_file()]
    db_path = sqlite_db_path()
    if db_path.exists():
        files.append(db_path)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(db_path) + suffix)
            if sidecar.exists():
                files.append(sidecar)
    return files
