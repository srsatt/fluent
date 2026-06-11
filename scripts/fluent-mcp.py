#!/usr/bin/env python3
"""
Minimal stdio MCP server for Fluent learner persistence.

Tools:
  - fluent_read_state: read learner stores plus computed fields
  - fluent_update_session: apply one complete session payload atomically
  - fluent_score_to_quality: map a 0-10 answer score to SM-2 quality 0-5
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from fluent_paths import force_utf8_io, sqlite_db_path  # noqa: E402
from fluent_storage import load_documents  # noqa: E402

force_utf8_io()


def _load_update_module():
    spec = importlib.util.spec_from_file_location("fluent_update_db", SCRIPT_DIR / "update-db.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load update-db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _next_session_id(sessions: list[dict[str, Any]]) -> str:
    if not sessions:
        return "session-001"
    import re

    last_id = sessions[-1].get("session_id", "")
    match = re.search(r"(\d+)", last_id)
    if match:
        return f"session-{int(match.group(1)) + 1:03d}"
    return f"session-{len(sessions) + 1:03d}"


DATABASE_KEYS = {
    "learner_profile",
    "progress_db",
    "mistakes_db",
    "mastery_db",
    "spaced_repetition",
    "session_log",
}


SEVERITY_RANK = {"critical": 0, "moderate": 1, "minor": 2}
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _limited_sessions(log: dict[str, Any], limit: int | None) -> dict[str, Any]:
    if limit is None:
        return log
    compact = dict(log)
    sessions = log.get("sessions", [])
    milestones = log.get("milestones", [])
    compact["sessions"] = sessions[-limit:] if limit > 0 else []
    compact["milestones"] = milestones[-limit:] if limit > 0 else []
    compact["sessions_omitted"] = max(0, len(sessions) - len(compact["sessions"]))
    compact["milestones_omitted"] = max(0, len(milestones) - len(compact["milestones"]))
    return compact


def _compact_progress(progress: dict[str, Any]) -> dict[str, Any]:
    return {
        "metadata": progress.get("metadata", {}),
        "overall_stats": progress.get("overall_stats", {}),
        "weekly_summary": progress.get("weekly_summary", [])[-4:],
        "accuracy_trend": progress.get("accuracy_trend", [])[-10:],
        "skill_progress": progress.get("skill_progress", {}),
    }


def _compact_mistakes(mistakes: dict[str, Any], limit: int) -> dict[str, Any]:
    patterns = mistakes.get("error_patterns", {})
    ranked = sorted(
        patterns.items(),
        key=lambda item: (
            SEVERITY_RANK.get(item[1].get("severity", "minor"), 9),
            item[1].get("mastery_level", 0),
            -item[1].get("frequency", 0),
            item[0],
        ),
    )
    return {
        "metadata": mistakes.get("metadata", {}),
        "error_patterns": dict(ranked[:limit]),
        "error_patterns_omitted": max(0, len(ranked) - limit),
    }


def _compact_spaced_repetition(sr: dict[str, Any], due_items: list[str], due_limit: int) -> dict[str, Any]:
    items = sr.get("items", {})
    included_ids = set(due_items[:due_limit])
    for item_id, item in sorted(
        items.items(),
        key=lambda entry: (
            PRIORITY_RANK.get(entry[1].get("priority", "medium"), 9),
            entry[1].get("due_date", ""),
            entry[0],
        ),
    ):
        if len(included_ids) >= due_limit:
            break
        if item.get("priority") == "high":
            included_ids.add(item_id)
    return {
        "metadata": sr.get("metadata", {}),
        "daily_limits": sr.get("daily_limits", {}),
        "review_queue_counts": {
            name: len(ids) for name, ids in sr.get("review_queue", {}).items()
        },
        "items": {item_id: items[item_id] for item_id in items if item_id in included_ids},
        "items_omitted": max(0, len(items) - len(included_ids)),
    }


def _compact_databases(databases: dict[str, Any], due_items: list[str], session_limit: int, pattern_limit: int, due_limit: int) -> dict[str, Any]:
    return {
        "learner_profile": databases.get("learner_profile", {}),
        "progress_db": _compact_progress(databases.get("progress_db", {})),
        "mistakes_db": _compact_mistakes(databases.get("mistakes_db", {}), pattern_limit),
        "mastery_db": databases.get("mastery_db", {}),
        "spaced_repetition": _compact_spaced_repetition(databases.get("spaced_repetition", {}), due_items, due_limit),
        "session_log": _limited_sessions(databases.get("session_log", {}), session_limit),
    }


def _filter_databases(databases: dict[str, Any], include: Any) -> dict[str, Any]:
    if not include:
        return databases
    requested = {name for name in include if name in DATABASE_KEYS}
    return {name: databases[name] for name in DATABASE_KEYS if name in requested and name in databases}


def read_state(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    view = arguments.get("view", "compact")
    if view not in {"compact", "full"}:
        raise ValueError("view must be 'compact' or 'full'")
    session_limit = _bounded_int(arguments.get("session_limit"), 5, 0, 50)
    pattern_limit = _bounded_int(arguments.get("pattern_limit"), 20, 1, 100)
    due_limit = _bounded_int(arguments.get("due_limit"), 20, 0, 100)

    databases, missing, backend = load_documents()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    sr = databases.get("spaced_repetition", {})
    items = sr.get("items", {})
    due_items = [item_id for item_id, item in items.items() if item.get("due_date", "") <= today]

    log = databases.get("session_log", {})
    sessions = log.get("sessions", [])

    profile = databases.get("learner_profile", {})
    last_updated = profile.get("last_updated", "")
    try:
        days_since = (now - datetime.strptime(last_updated, "%Y-%m-%d")).days if last_updated else None
    except ValueError:
        days_since = None

    if view == "compact":
        output_databases = _compact_databases(databases, due_items, session_limit, pattern_limit, due_limit)
    else:
        full_session_limit = arguments.get("session_limit")
        output_databases = dict(databases)
        if full_session_limit is not None:
            output_databases["session_log"] = _limited_sessions(
                output_databases.get("session_log", {}),
                _bounded_int(full_session_limit, 5, 0, 1000),
            )
    output_databases = _filter_databases(output_databases, arguments.get("include_databases"))

    result = {
        "view": view,
        "databases": output_databases,
        "computed": {
            "today": today,
            "due_reviews_count": len(due_items),
            "due_review_items": due_items[:due_limit],
            "due_review_items_omitted": max(0, len(due_items) - due_limit),
            "next_session_id": _next_session_id(sessions),
            "streak_active": last_updated in (today, yesterday),
            "days_since_last_session": days_since,
            "storage_backend": backend,
            "sqlite_path": str(sqlite_db_path()) if backend == "sql" else None,
        },
    }
    if missing:
        result["_warnings"] = [f"Missing file: {m}" for m in missing]
    return result


def score_to_quality(score: float | int) -> int:
    value = int(float(score) // 2)
    return max(0, min(5, value))


TOOLS: list[dict[str, Any]] = [
    {
        "name": "fluent_read_state",
        "description": "Read Fluent learner state plus computed fields. Compact view is default to keep token usage stable as history grows; pass view=full when complete stores are required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "view": {
                    "type": "string",
                    "enum": ["compact", "full"],
                    "default": "compact",
                    "description": "compact returns bounded history and review detail; full returns complete stores unless a session_limit is provided.",
                },
                "session_limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 1000,
                    "default": 5,
                    "description": "Number of recent session_log entries to include. In full view, omit this field to include all sessions.",
                },
                "pattern_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                    "description": "Maximum mistake patterns included in compact view.",
                },
                "due_limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "default": 20,
                    "description": "Maximum due review ids and detailed review items included.",
                },
                "include_databases": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": sorted(DATABASE_KEYS),
                    },
                    "description": "Optional subset of logical stores to include.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "fluent_update_session",
        "description": "Apply one complete Fluent practice-session payload atomically. This updates profile, progress, mistakes, mastery, spaced repetition, and session log.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session": {
                    "type": "object",
                    "description": "The same payload accepted by scripts/update-db.py. Required keys: session_id and date.",
                }
            },
            "required": ["session"],
            "additionalProperties": False,
        },
    },
    {
        "name": "fluent_score_to_quality",
        "description": "Map a 0-10 answer score to SM-2 review quality 0-5 using floor(score / 2), clamped to 0..5.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Answer score from 0 to 10.",
                }
            },
            "required": ["score"],
            "additionalProperties": False,
        },
    },
]


def _content(data: Any) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(data, ensure_ascii=False, indent=2),
            }
        ],
        "structuredContent": data,
    }


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "fluent_read_state":
        return _content(read_state(arguments))
    if name == "fluent_update_session":
        session = arguments.get("session")
        if not isinstance(session, dict):
            raise ValueError("fluent_update_session requires a session object")
        update_db = _load_update_module()
        return _content(update_db.apply_session_update(session))
    if name == "fluent_score_to_quality":
        return _content({"score": arguments.get("score"), "quality": score_to_quality(arguments["score"])})
    raise ValueError(f"Unknown tool: {name}")


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "serverInfo": {"name": "fluent", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        try:
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = handle(request)
        except Exception as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
