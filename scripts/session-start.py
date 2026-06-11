#!/usr/bin/env python3
"""
Fluent Session Start Hook
Displays welcome message with learner stats and due reviews
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import force_utf8_io  # noqa: E402
from fluent_storage import load_documents  # noqa: E402

force_utf8_io()


def main():
    # Read hook input from stdin (optional for SessionStart)
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    databases, missing, _backend = load_documents()
    profile = databases.get("learner_profile", {})

    if missing or not profile:
        print("[Fluent] 🌍 Welcome to Fluent - The AI Language Learning Kit!")
        print("[Fluent] 📝 Run /fluent-setup to create your personalized learning profile")
        sys.exit(0)

    try:
        learner = profile.get("learner", {})
        name = learner.get("name", "Learner")
        target_lang = learner.get("target_language", "your target language")
        current_level = learner.get("current_level", "...")
        target_level = learner.get("target_level", "...")
        streak = profile.get("current_streak_days", 0)

        print(f"[Fluent] 🌍 Welcome back, {name}!")
        print(f"[Fluent] 📚 Learning: {target_lang}")
        print(f"[Fluent] 🎯 Level: {current_level} → {target_level}")
        print(f"[Fluent] 🔥 Streak: {streak} days")

        sr_data = databases.get("spaced_repetition", {})
        if sr_data:
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                due_count = 0

                items = sr_data.get("items", {})
                iterable = items.values() if isinstance(items, dict) else items
                for item in iterable:
                    due = item.get("due_date") or item.get("next_review_date", "")
                    if due and due <= today:
                        due_count += 1

                if due_count > 0:
                    print(f"[Fluent] 📅 {due_count} items due for review today - Run /fluent-review!")

            except Exception:
                pass

    except Exception as e:
        print(f"[Fluent] Error loading profile: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
