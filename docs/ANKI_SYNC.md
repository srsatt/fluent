# Anki Sync Strategy

Fluent can feed Anki without making Anki the source of truth. Fluent owns tutoring context, mistakes, mastery, and SM-2 scheduling; Anki is an optional review surface.

## Modes

### TSV export

Works without add-ons:

```bash
python3 scripts/anki-sync.py export-tsv --output data/fluent-anki.tsv
```

Import the TSV in Anki and map fields to a Basic-style note type. The export includes:

- front
- back
- context
- Fluent item id
- tags

### AnkiConnect

If Anki is open and the AnkiConnect add-on is installed:

```bash
python3 scripts/anki-sync.py status
python3 scripts/anki-sync.py push --deck Fluent
```

The push creates or updates notes in a `Fluent Basic` note type with these fields:

- Front
- Back
- Context
- FluentId

## Sync Ownership

Current implementation is one-way: Fluent -> Anki. That avoids corrupting Fluent scheduling with partial Anki state. A later two-way sync should map Anki review results into `review_results[]` only after duplicate detection and conflict rules are explicit.

## Prompt Rule

The tutor may suggest Anki sync after vocabulary-heavy sessions, but should not push to Anki without learner confirmation.
