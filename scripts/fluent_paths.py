"""
Fluent path resolution — supports dual-mode (clone vs plugin install).

Data directory resolution precedence:
  1. $FLUENT_DATA_DIR if set (absolutized)
  2. $FLUENT_PROJECT_DIR/data if that dir holds learner-profile.json
  3. $CLAUDE_PROJECT_DIR/data if that dir holds learner-profile.json (clone mode, non-repo cwd)
  4. ./data if ./data/learner-profile.json exists (clone mode, in-repo cwd)
  5. ~/.fluent/data (generic fallback)
  6. ~/.claude/fluent-data (legacy plugin fallback, when it already exists)

Plugin-root resolution precedence:
  1. $FLUENT_PLUGIN_ROOT if set
  2. $CLAUDE_PLUGIN_ROOT if set
  3. $FLUENT_PROJECT_DIR if set
  4. $CLAUDE_PROJECT_DIR if set
  5. parent of this file's .claude/ dir (dev-run fallback)

Pure resolvers (data_dir / plugin_root / backups_dir) do not create directories.
Call ensure_data_dir() before writing.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


def _repo_root_from_file() -> Path:
    """Find the repo/plugin root from this script location."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "TUTOR.md").exists() or (parent / ".claude-plugin").exists():
            return parent
    return here.parents[1]


@lru_cache(maxsize=1)
def dotenv_values() -> dict[str, str]:
    """Read simple KEY=value settings from repo .env, without overriding env vars."""
    values: dict[str, str] = {}
    candidates = [plugin_root() / ".env", Path.cwd() / ".env"]
    for path in candidates:
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in values:
                values[key] = value
    return values


def setting(*names: str, default: str | None = None) -> str | None:
    """Read the first matching environment or .env setting."""
    env_values = os.environ
    dotenv = dotenv_values()
    for name in names:
        if name in env_values:
            return env_values[name]
        if name in dotenv:
            return dotenv[name]
    return default


def force_utf8_io() -> None:
    """Make stdout/stderr UTF-8 so emoji/CJK output doesn't crash on Windows.

    Windows consoles default to a legacy code page (cp1252/gbk); printing the
    emoji in the hook summaries raises UnicodeEncodeError there. No-op on
    platforms whose streams are already UTF-8 or predate ``reconfigure``.
    Call once at the top of any hook that prints.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


@lru_cache(maxsize=1)
def data_dir() -> Path:
    """Resolve the runtime data directory (pure — does not create it)."""
    env = os.environ.get("FLUENT_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()

    for project_env in ("FLUENT_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        project = os.environ.get(project_env)
        if not project:
            continue
        candidate = (Path(project) / "data").resolve()
        if (candidate / "learner-profile.json").exists():
            return candidate

    cwd_data = (Path.cwd() / "data").resolve()
    if (cwd_data / "learner-profile.json").exists():
        return cwd_data

    legacy = (Path.home() / ".claude" / "fluent-data").resolve()
    if (legacy / "learner-profile.json").exists():
        return legacy

    return (Path.home() / ".fluent" / "data").resolve()


def ensure_data_dir() -> Path:
    """Resolve the data directory and create it if missing. Call before writing."""
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


@lru_cache(maxsize=1)
def plugin_root() -> Path:
    """Resolve the plugin/repo root directory."""
    for env_name in ("FLUENT_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT",
                     "FLUENT_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        env = os.environ.get(env_name)
        if env:
            return Path(env).resolve()
    return _repo_root_from_file()


@lru_cache(maxsize=1)
def backups_dir() -> Path:
    """Resolve the backups directory. Always nested inside data_dir to avoid collisions
    when the fallback ~/.claude/fluent-data is used (the parent ~/.claude/ is shared
    across plugins)."""
    return data_dir() / ".backups"


def ensure_backups_dir() -> Path:
    """Resolve the backups directory and create it if missing."""
    b = backups_dir()
    b.mkdir(parents=True, exist_ok=True)
    return b


def db_backend() -> str:
    """Return configured storage backend: sql (default) or json."""
    value = setting("FLUENT_DB", "FLUENT_DB_BACKEND", "DB", "db", default="sql")
    normalized = (value or "sql").strip().lower()
    if normalized in ("sqlite", "sql"):
        return "sql"
    if normalized == "json":
        return "json"
    raise ValueError(f"Unsupported Fluent DB backend: {value!r}. Use sql or json.")


def sqlite_db_path() -> Path:
    """Resolve SQLite store path."""
    configured = setting("FLUENT_SQLITE_PATH", "FLUENT_DB_PATH", "DB_PATH", "db_path")
    if configured:
        return Path(configured).expanduser().resolve()
    return data_dir() / "fluent.sqlite"
