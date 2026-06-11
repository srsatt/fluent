#!/usr/bin/env python3
"""
Fluent Session End Hook
Creates daily backups and displays session summary
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import ensure_backups_dir, force_utf8_io  # noqa: E402
from fluent_storage import load_documents, storage_files_for_backup  # noqa: E402

force_utf8_io()


def main():
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    backup_dir = ensure_backups_dir() / datetime.now().strftime("%Y%m%d")
    backup_dir.mkdir(parents=True, exist_ok=True)

    backed_up = []
    for store_file in storage_files_for_backup():
        try:
            shutil.copy2(store_file, backup_dir / store_file.name)
            backed_up.append(store_file.name)
        except Exception as e:
            print(f"[Fluent] Warning: Could not backup {store_file}: {e}", file=sys.stderr)

    if backed_up:
        print(f"[Fluent] 📦 Session backup created: {backup_dir}/")
        print(f"[Fluent] 💾 Files backed up: {', '.join(backed_up)}")

    try:
        databases, missing, _backend = load_documents()
        profile = databases.get("learner_profile", {})

        if profile and not missing:
            streak = profile.get("current_streak_days", 0)
            total_sessions = profile.get("total_sessions", 0)

            print(f"[Fluent] 🔥 Current streak: {streak} days")
            print(f"[Fluent] 📊 Total sessions: {total_sessions}")
            print(f"[Fluent] 👋 Great work today!")

    except Exception as e:
        print(f"[Fluent] Could not read stats: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
