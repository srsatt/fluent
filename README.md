# Fluent

Fluent is a local, agent-driven language learning kit. It gives an AI agent a tutoring protocol, practice skills, spaced-repetition tracking, session logs, optional SQLite export, and optional Anki export/sync.

It is designed for Codex, Claude Code, Gemini CLI, and similar agent runtimes. The `.claude/` directory name is kept for Claude Code plugin compatibility, but the tutor instructions are generic.

## Quick Start

### Use from a clone

```bash
git clone https://github.com/m98/fluent.git
cd fluent
```

Open the repo in your agent runtime. Codex reads `AGENTS.md`; other agents should start from `TUTOR.md`.

Then run:

```text
/fluent-setup
/fluent-learn
```

### Claude Code plugin install

```bash
claude plugin marketplace add m98/fluent
claude plugin install fluent@m98
```

Restart Claude Code, then run `/fluent-setup`.

## How Agents Should Use It

Read these files in order:

1. `TUTOR.md` - role, session contract, feedback style, critical rules
2. `LEARNING_SYSTEM.md` - methodology, storage boundary, SM-2, session flow
3. `PRACTICE.md` - how to analyze stored session history and choose the next lesson
4. `skills/<skill>/SKILL.md` - command-specific workflow

For Codex, slash commands are just learner intent. When the learner types `/fluent-writing`, read `skills/fluent-writing/SKILL.md` and follow it.

## Commands

| Command | Purpose |
|---------|---------|
| `/fluent-setup` | Create or update the learner profile |
| `/fluent-learn` | Adaptive mixed practice |
| `/fluent-review` | Due spaced-repetition reviews |
| `/fluent-vocab` | Vocabulary drills |
| `/fluent-writing` | Writing tasks and corrections |
| `/fluent-speaking` | Typed conversation practice |
| `/fluent-conceptualisation` | Discover and practice one needed grammar rule |
| `/fluent-reading` | Reading comprehension |
| `/fluent-rss` | Study real audio/video RSS content; use `/fluent-rss setup` to store feeds and transcription settings |
| `/fluent-progress` | Read-only progress dashboard |
| `/fluent-anki-sync` | Export or push review items to Anki |

Helper skills:

- `fluent-feedback-formatter`
- `fluent-session-analyzer`

## Learning Model

Fluent is built around adult language learning:

- realistic tasks before abstract drills
- active recall before explanation
- spaced repetition for durable memory
- interleaving to build discrimination
- immediate, selective feedback
- CEFR-aware task difficulty
- reflection and self-correction

The goal is not to maximize chat volume. The goal is to help the learner complete real target-language tasks with increasing independence.

## Data

The default source of truth is SQLite, configured in `.env`:

```dotenv
db=sql
```

Set `db=json` to use the legacy JSON-file backend. Both backends expose the same logical learner stores:

| File | Purpose |
|------|---------|
| `learner-profile.json` | profile, goals, preferences, streak, personalization facts |
| `progress-db.json` | stats and trends |
| `mistakes-db.json` | recurring error patterns |
| `mastery-db.json` | mastery levels |
| `spaced-repetition.json` | SM-2 items and queues |
| `session-log.json` | session history |

Agents should not hand-edit these during lessons. Prefer MCP tools:

```text
fluent_read_state
fluent_update_session
fluent_get_user_profile
fluent_persist_profile_fact
fluent_internalize_profile
fluent_score_to_quality
```

For runtimes without MCP, use the CLI fallback:

```bash
python3 scripts/read-db.py
python3 scripts/update-db.py
```

The persistence boundary is intentional. Prompts and skills use the same API whether the backend is SQL or JSON.
RSS feed subscriptions are stored under `learner-profile.json` preferences by `scripts/rss-setup.py`; machine-local STT settings are stored in `rss-stt-settings.json` in the active data directory. Media previews and transcripts use `scripts/rss-preview.py` and `scripts/rss-transcribe.py`.

### Data Directory Resolution

First match wins:

1. `$FLUENT_DATA_DIR`
2. `$FLUENT_PROJECT_DIR/data/` when it contains a profile
3. `$CLAUDE_PROJECT_DIR/data/` when it contains a profile
4. `./data/` when it contains a profile
5. legacy `~/.claude/fluent-data/` if it already exists
6. `~/.fluent/data/`

Check the active directory:

```bash
python3 -c "import sys; sys.path.insert(0, 'scripts'); from fluent_paths import data_dir; print(data_dir())"
```

## SQLite

Explicit SQLite export:

```bash
python3 scripts/sqlite-store.py export --db data/fluent.sqlite
```

Restore JSON from that mirror:

```bash
python3 scripts/sqlite-store.py import --db data/fluent.sqlite --output-dir data-restored
```

See `docs/STORAGE.md`.

## Anki

Export review items to TSV:

```bash
python3 scripts/anki-sync.py export-tsv --output data/fluent-anki.tsv
```

If Anki is open with AnkiConnect installed:

```bash
python3 scripts/anki-sync.py status
python3 scripts/anki-sync.py push --deck Fluent
```

Fluent remains the source of truth. Anki sync is currently one-way: Fluent -> Anki. See `docs/ANKI_SYNC.md`.

## Repository Layout

| Path | Purpose |
|------|---------|
| `TUTOR.md` | generic tutor prompt |
| `AGENTS.md` | Codex/agent integration guide |
| `LEARNING_SYSTEM.md` | teaching methodology |
| `PRACTICE.md` | session analysis guide |
| `skills/` | Fluent skill workflows |
| `scripts/` | storage, backup, Anki, SQLite scripts |
| `.claude/` | Claude Code harness files and symlinks |
| `.codex/` | Codex harness files and symlinks |
| `.claude/references/` | reusable templates |
| `data-examples/` | JSON templates |
| `docs/` | technical docs |

## Privacy

All learner data stays local unless the learner explicitly exports it or pushes to Anki. Personal data, SQLite databases, TSV exports, and backups are ignored by git.

## Development

Run tests with:

```bash
python3 -m unittest discover tests
```

The scripts use only the Python standard library.

## License

MIT. See `LICENSE`.
