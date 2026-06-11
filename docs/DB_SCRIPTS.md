# Database Helper Scripts

Two Python scripts under `scripts/` are the supported persistence API:

| Script | Purpose |
|--------|---------|
| `read-db.py` | Load all learner stores plus computed fields |
| `update-db.py` | Apply one session report atomically |

The `scripts` and `.codex/scripts` paths are harness symlinks to the same top-level scripts.

## Reading

From the repo root:

```bash
python3 scripts/read-db.py
```

From another working directory, resolve the root first:

```bash
python3 "${FLUENT_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${FLUENT_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}}}/scripts/read-db.py"
```

Output shape:

```json
{
  "databases": {
    "learner_profile": {},
    "progress_db": {},
    "mistakes_db": {},
    "mastery_db": {},
    "spaced_repetition": {},
    "session_log": {}
  },
  "computed": {
    "today": "2026-04-24",
    "due_reviews_count": 3,
    "due_review_items": ["vocab_dag"],
    "next_session_id": "session-005",
    "streak_active": true,
    "days_since_last_session": 1
  }
}
```

Exit codes:

- `0` success
- `1` partial result with missing files
- `2` critical error

## Writing

Call once at session end:

```bash
python3 scripts/update-db.py <<'EOF'
{
  "session_id": "session-005",
  "date": "2026-04-24",
  "duration_minutes": 20,
  "command_used": "/fluent-learn",
  "skills_practiced": ["vocabulary", "writing"],
  "skill_scores": {
    "vocabulary": { "exercises": 5, "correct": 4, "time_minutes": 10 },
    "writing": { "exercises": 3, "correct": 2, "time_minutes": 10 }
  },
  "errors": [
    {
      "pattern_id": "verb_conjugation_3rd_person",
      "category": "grammar",
      "subcategory": "verb_conjugation",
      "your_answer": "Hij spreek",
      "correct_answer": "Hij spreekt",
      "context": "3rd person singular",
      "difficulty_score": 0.7,
      "severity": "critical"
    }
  ],
  "new_vocabulary": [
    {
      "item_id": "het_huis",
      "item_type": "vocabulary",
      "content": "het huis",
      "answer": "the house",
      "category": "essential_nouns",
      "difficulty": "A1",
      "initial_quality": 4,
      "priority": "medium"
    }
  ],
  "review_results": [
    { "item_id": "vocab_dag", "quality": 4 }
  ],
  "topics_covered": ["articles", "house_vocabulary"],
  "breakthroughs": ["First correct use of a target article"],
  "focus_next_session": ["Article gender drill"],
  "session_notes": "Strong session."
}
EOF
```

Required fields:

- `session_id`
- `date`

Everything else is optional.

## Side Effects

- backs up current stores to `.backups/pre-update-<session_id>/`
- writes with `.tmp` + `fsync` + atomic rename
- rebuilds spaced-repetition queues from item due dates
- updates streaks, progress, mastery, errors, and session log consistently

Exit codes:

- `0` success
- `1` validation error, no files touched
- `2` I/O or logic error, no files touched

## Data Model Notes

- `learner-profile.json` stores confidence per skill as 0-100 integers.
- `progress-db.json` stores accuracy values as 0.0-1.0 floats.
- `session-log.json` sessions use `session-NNN` ids.
- `spaced-repetition.json` items preserve content, answer, category, priority, review history, mastery, and SM-2 fields.

## Backend

SQL is default (`db=sql` in `.env`). Use `db=json` for the legacy JSON backend. See `docs/STORAGE.md`.
