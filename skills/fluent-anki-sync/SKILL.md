---
name: fluent-anki-sync
description: Export Fluent spaced-repetition items to Anki or push them through AnkiConnect. Use when the learner invokes /fluent-anki-sync, asks to export flashcards, sync vocabulary with Anki, create an Anki deck, or review Fluent items in Anki. Confirms before writing to Anki and treats Fluent as the source of truth.
allowed-tools: Read, Bash, AskUserQuestion
disable-model-invocation: true
---

# Anki Sync

## Overview

Create Anki cards from Fluent spaced-repetition items. The safe default is TSV export. Live Anki sync is optional and requires Anki running with the AnkiConnect add-on.

Fluent remains the source of truth. Do not import Anki review history into Fluent unless a future two-way workflow is explicitly implemented.

## When to Use

Use only when the learner explicitly asks for Anki sync/export or types `/fluent-anki-sync`. Do not auto-push cards after a lesson.

## Workflow

### 1. Load current state

```bash
python3 scripts/read-db.py
```

Confirm there are spaced-repetition items. If none exist, suggest `/fluent-vocab` or `/fluent-learn` first.

### 2. Ask for mode

Offer:

1. TSV export - works with any Anki install, no add-ons.
2. AnkiConnect push - requires Anki open and AnkiConnect installed.
3. Dry run - show how many notes would be exported.

Default to TSV export unless the learner specifically wants live sync.

### 3. TSV export

```bash
python3 scripts/anki-sync.py export-tsv --output data/fluent-anki.tsv
```

Tell the learner the file path and fields: `Front`, `Back`, `Context`, `FluentId`, `Tags`.

### 4. AnkiConnect push

First check availability:

```bash
python3 scripts/anki-sync.py status
```

If available, confirm before pushing:

```bash
python3 scripts/anki-sync.py push --deck Fluent
```

The script creates or updates notes in the `Fluent Basic` note type.

### 5. Session note

This is a maintenance action, not a practice session. Do not call `update-db.py` unless the learner also practiced items in the same interaction.

## Constraints

- Ask before live Anki writes.
- Do not delete Anki notes.
- Do not mark Fluent items reviewed just because they were exported.
- Do not create duplicate decks when the learner names a deck.
- Keep language-learning context in Fluent; Anki cards should be concise prompts.

## Troubleshooting

- `Cannot reach AnkiConnect`: open Anki, install/enable AnkiConnect, then retry.
- TSV import shows one field: confirm Anki is using tab separation.
- Duplicate notes: use the `FluentId` field to identify generated cards.
