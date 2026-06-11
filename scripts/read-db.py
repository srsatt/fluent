#!/usr/bin/env python3
"""
Fluent DB Reader Script
Loads learner stores and outputs a single JSON object to stdout.

Usage:
    python3 scripts/read-db.py [--view compact|full] [--session-limit N]

Exit codes: 0=success, 1=partial (some files missing), 2=critical error
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import force_utf8_io  # noqa: E402

force_utf8_io()


def load_state_reader():
    script_dir = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("fluent_mcp", script_dir / "fluent-mcp.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load fluent-mcp.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_state


def main():
    parser = argparse.ArgumentParser(description="Read Fluent learner state.")
    parser.add_argument("--view", choices=["compact", "full"], default="compact")
    parser.add_argument("--session-limit", type=int, default=None)
    parser.add_argument("--pattern-limit", type=int, default=20)
    parser.add_argument("--due-limit", type=int, default=20)
    parser.add_argument(
        "--include-databases",
        default="",
        help="Comma-separated logical stores to include, for example learner_profile,session_log",
    )
    args = parser.parse_args()

    request = {
        "view": args.view,
        "pattern_limit": args.pattern_limit,
        "due_limit": args.due_limit,
    }
    if args.session_limit is not None:
        request["session_limit"] = args.session_limit
    if args.include_databases:
        request["include_databases"] = [
            value.strip() for value in args.include_databases.split(",") if value.strip()
        ]

    result = load_state_reader()(request)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(1 if result.get("_warnings") else 0)


if __name__ == "__main__":
    main()
