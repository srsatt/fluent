# Database Persistence API

The Fluent MCP server is the preferred persistence API for agent runtimes:

| MCP tool | Purpose |
|----------|---------|
| `fluent_read_state` | Load compact or full learner state plus computed fields |
| `fluent_update_session` | Apply one session report atomically |
| `fluent_get_user_profile` | Read compact learner profile plus personalization summary |
| `fluent_persist_profile_fact` | Store one explicit durable learner fact |
| `fluent_internalize_profile` | Refresh compact personalization profile from stored facts |
| `fluent_score_to_quality` | Map a 0-10 score to SM-2 quality 0-5 |

Start the repo-local server with:

```bash
python3 scripts/fluent-mcp.py
```

The same operations are still available as CLI fallback scripts:

| Script | Purpose |
|--------|---------|
| `read-db.py` | Load compact or full learner state plus computed fields |
| `update-db.py` | Apply one session report atomically |

The `scripts` and `.codex/scripts` paths are harness symlinks to the same top-level scripts.

## MCP Reading

Call `fluent_read_state` with `{}` for the default compact view. Compact state bounds session history, due-review details, and mistake patterns so token usage stays stable as the learner history grows.

Optional arguments:

```json
{
  "view": "compact",
  "session_limit": 5,
  "pattern_limit": 20,
  "due_limit": 20,
  "include_databases": ["learner_profile", "session_log"]
}
```

Use `view: "full"` only for migrations, debugging, or bounded audits that genuinely need complete stores. In full view, omit `session_limit` to include all sessions, or pass a limit to include only the most recent entries.

## CLI Reading

From the repo root:

```bash
python3 scripts/read-db.py
python3 scripts/read-db.py --view full --session-limit 5 --include-databases session_log
```

From another working directory, resolve the root first:

```bash
python3 "${FLUENT_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${FLUENT_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}}}/scripts/read-db.py"
```

Output shape:

```json
{
  "view": "compact",
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
    "due_review_items_omitted": 0,
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

## MCP Writing

Call `fluent_update_session` with:

```json
{ "session": { "...": "payload shown below" } }
```

Use `fluent_score_to_quality` to convert per-answer scores into `review_results[].quality`.

For personalization outside a lesson, call `fluent_persist_profile_fact`:

```json
{
  "text": "The learner has a German tutor once a week.",
  "category": "lifestyle",
  "confidence": 0.9,
  "source": "learner-correction"
}
```

Call `fluent_internalize_profile` only occasionally to refresh the compact tutor-facing profile from stored facts. During lessons, prefer batching new facts in `profile_facts[]` on the normal `fluent_update_session` payload.

## CLI Writing

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
  "profile_facts": [
    {
      "text": "The learner likes appointment and bureaucracy scenarios because of the B1 citizenship goal.",
      "category": "preferred_context",
      "confidence": 0.8,
      "evidence": "Learner chose citizenship/application practice."
    }
  ],
  "topics_covered": ["articles", "house_vocabulary"],
  "breakthroughs": ["First correct use of a target article"],
  "focus_next_session": ["Article gender drill"],
  "exercises": [
    {
      "prompt": "Translate: the house",
      "learner_answer": "het huis",
      "correct_answer": "het huis",
      "feedback": "Correct.",
      "score": 10
    }
  ],
  "session_notes": "Strong session."
}
EOF
```

Required fields:

- `session_id`
- `date`

Everything else is optional.

Use `exercises[]` for any per-turn detail that future planning should retain. Do not create separate result files; the SQLite-backed session log is the durable session record.

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
- `learner-profile.json` stores personalization facts in `personalization.facts[]` and the compact tutor-facing summary in `personalization.profile`.
- `progress-db.json` stores accuracy values as 0.0-1.0 floats.
- `session-log.json` sessions use `session-NNN` ids.
- `spaced-repetition.json` items preserve content, answer, category, priority, review history, mastery, and SM-2 fields.

## Backend

SQL is default (`db=sql` in `.env`). Use `db=json` for the legacy JSON backend. See `docs/STORAGE.md`.
