# Fluent Hooks and Utilities

This directory contains generic Fluent utility scripts. The path is `.claude/` for Claude Code plugin compatibility, but Codex and other local agents can call the same scripts directly.

## Core Scripts

| Script | Purpose |
|--------|---------|
| `fluent-mcp.py` | Stdio MCP server exposing `fluent_read_state`, `fluent_update_session`, and `fluent_score_to_quality` |
| `read-db.py` | CLI fallback: read compact or full learner state and computed fields |
| `update-db.py` | CLI fallback: apply one session payload atomically |
| `validate-data.py` | Validate and back up JSON files after edits |
| `session-start.py` | Show current learner status for hook-enabled runtimes |
| `session-end.py` | Create a daily backup and summary |
| `precompact-backup.sh` | Safety backup before context compaction |
| `sqlite-store.py` | Export/import SQLite stores |
| `anki-sync.py` | Export TSV or push cards through AnkiConnect |

## Data Directory Resolution

`fluent_paths.py` resolves data in this order:

1. `$FLUENT_DATA_DIR`
2. `$FLUENT_PROJECT_DIR/data` when it contains a profile
3. `$CLAUDE_PROJECT_DIR/data` when it contains a profile
4. `./data` when it contains a profile
5. legacy `~/.claude/fluent-data` if it already exists
6. `~/.fluent/data`

Use `ensure_data_dir()` before writing.

## Agent Usage

Prefer MCP tools in MCP-capable runtimes:

```text
fluent_read_state
fluent_update_session
fluent_score_to_quality
```

From the repo root without MCP:

```bash
python3 scripts/read-db.py
python3 scripts/read-db.py --view full --session-limit 5
python3 scripts/update-db.py
```

When the root is not the working directory:

```bash
python3 "${FLUENT_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${FLUENT_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}}}/scripts/read-db.py"
```

## Hook Registration

Claude Code can register hooks through:

- `.claude/settings.json` in clone mode
- `.claude/hooks/hooks.json` in plugin mode

Other agent runtimes can ignore hook registration and call the scripts explicitly.

## Backups

Backups are written under the resolved data directory:

- `.backups/pre-update-<session_id>/`
- `.backups/YYYYMMDD/`
- `.backups/precompact/`

Personal data and backups are ignored by git.

## SQLite

```bash
python3 scripts/sqlite-store.py export --db data/fluent.sqlite
python3 scripts/sqlite-store.py import --db data/fluent.sqlite --output-dir data-restored
```

See `docs/STORAGE.md`.

## Anki

```bash
python3 scripts/anki-sync.py export-tsv --output data/fluent-anki.tsv
python3 scripts/anki-sync.py status
python3 scripts/anki-sync.py push --deck Fluent
```

Live Anki writes require explicit learner confirmation. See `docs/ANKI_SYNC.md`.
