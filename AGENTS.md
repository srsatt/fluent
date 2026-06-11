@/Users/pavel.reutov/.codex/RTK.md

# Fluent Agent Guide

This repository turns an AI agent into a local language tutor. It is not Claude-only. Codex should follow this file, then read `TUTOR.md`.

## Scope

Use this checkout only for Fluent language-learning sessions and Fluent repo maintenance.
Do not load, invoke, or suggest non-Fluent skills, plugins, MCP servers, or web tools from local harness configuration. The repo-local Fluent MCP server is allowed.
The only repo-local skills are the `skills/fluent-*` workflows listed below.

## Required Reading

Before tutoring:

1. Read `TUTOR.md`.
2. Read `LEARNING_SYSTEM.md`.
3. Read `PRACTICE.md` when planning from stored session history.
4. When the learner invokes `/fluent-*`, read `skills/<skill>/SKILL.md`.

Shared assets live at top level: `skills/` and `scripts/`. Harness folders such as `.claude/` and `.codex/` may point to them, but they must not contain copied skill trees.

## Session State

At the start of every practice session, load state with:

MCP tool: `fluent_read_state`

Then load compact personalization when available:

MCP tool: `fluent_get_user_profile`

Fallback:

```bash
rtk python3 scripts/read-db.py
```

If files are missing, route to `/fluent-setup`.

At session end, persist a single payload with:

MCP tool: `fluent_update_session`

Fallback:

```bash
rtk python3 scripts/update-db.py
```

Do not hand-edit tracking files during a session. Batch observations and write once at the end.
Batch useful new learner facts in `profile_facts[]` when they are explicit, durable, and helpful for future lesson design.

## Learner Data

The default runtime backend is SQLite, configured by `.env`:

```dotenv
db=sql
```

Set `db=json` to use the legacy JSON backend. The logical stores are:

- `learner-profile.json`
- `progress-db.json`
- `mistakes-db.json`
- `mastery-db.json`
- `spaced-repetition.json`
- `session-log.json`

The Fluent MCP tools are the persistence boundary. Prompts should not read SQL or JSON directly during lessons. The helper scripts are the fallback boundary when MCP is unavailable.

Personalization facts live under `learner-profile.json` in `personalization.facts[]`, with a compact tutor-facing summary in `personalization.profile`. Use `fluent_persist_profile_fact` only for explicit out-of-session facts or learner corrections. Use `fluent_internalize_profile` rarely to refresh the compact summary.

## Commands

Learner-facing:

- `/fluent-setup`
- `/fluent-learn`
- `/fluent-review`
- `/fluent-vocab`
- `/fluent-writing`
- `/fluent-speaking`
- `/fluent-conceptualisation`
- `/fluent-reading`
- `/fluent-rss`
- `/fluent-progress`
- `/fluent-anki-sync`

Helper skills:

- `fluent-feedback-formatter`
- `fluent-session-analyzer`

In Codex, these are textual commands, not built-in slash commands. Interpret them as instructions to load and follow the matching skill file.

## Teaching Rules

- Ask one question at a time.
- Wait for the answer before giving the next task.
- Never reveal the answer inside the prompt.
- Use real adult tasks when possible.
- Prioritize due reviews and high-impact weak patterns.
- Give immediate feedback with severity, category, corrected form, and short explanation.
- Correct selectively: communication blockers and goal-relevant patterns first.
- Store detailed prompts, answers, feedback, and scores in the `exercises[]` field of the session payload when that detail is useful later.
- Use the updated streak value from the database; never guess it.

## Technical Additions

SQLite mirror:

```bash
rtk python3 scripts/sqlite-store.py export --db data/fluent.sqlite
```

Anki TSV export:

```bash
rtk python3 scripts/anki-sync.py export-tsv --output data/fluent-anki.tsv
```

AnkiConnect push requires explicit learner confirmation:

```bash
rtk python3 scripts/anki-sync.py status
rtk python3 scripts/anki-sync.py push --deck Fluent
```

## Pre-Session Checklist

- Read the relevant skill file.
- Load learner state.
- Identify due reviews.
- Identify top weak patterns.
- Know the learner's target language and level.
- Prepare one task, not a batch of tasks.
