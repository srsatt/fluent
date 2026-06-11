# Data Directory

This directory is intentionally empty in git. `/fluent-setup` creates private learner data here when you use Fluent from a clone.

## Runtime Stores

- `learner-profile.json` - learner name, languages, goals, preferences, streak
- `progress-db.json` - statistics and trends
- `mistakes-db.json` - recurring error patterns and examples
- `mastery-db.json` - skill and pattern mastery
- `spaced-repetition.json` - SM-2 review items and queues
- `session-log.json` - session history

Agents should use the Fluent MCP tools (`fluent_read_state`, `fluent_update_session`) rather than editing stores directly during lessons. Use `scripts/read-db.py` and `scripts/update-db.py` only as a fallback when MCP is unavailable.

## Private by Default

The repo ignores:

- `data/*.json`
- JSON backups
- SQLite mirrors
- Anki TSV exports

All data stays on your machine unless you explicitly export or sync it.

## Optional Exports

SQLite mirror:

```bash
python3 scripts/sqlite-store.py export --db data/fluent.sqlite
```

Anki TSV:

```bash
python3 scripts/anki-sync.py export-tsv --output data/fluent-anki.tsv
```

## Reset

To start over, back up this directory, delete the generated data files, and run `/fluent-setup` again.
