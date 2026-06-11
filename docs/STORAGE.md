# Fluent Storage Strategy

Fluent uses SQL by default and keeps JSON available as a compatibility backend.

## Configuration

Runtime backend is configured in `.env`:

```dotenv
db=sql
```

Allowed values:

- `sql` - default SQLite backend
- `json` - legacy JSON-file backend

You can also set the backend through environment variables:

- `FLUENT_DB=sql`
- `FLUENT_DB_BACKEND=sql`
- `DB=sql`
- `db=sql`

An explicit SQLite path can be set with `db_path=...` or `FLUENT_DB_PATH=...`.

## Boundary

Prompts and skills must use the helper boundary:

```bash
python3 scripts/read-db.py
python3 scripts/update-db.py
```

Do not teach prompts to read SQLite or JSON directly. Only helper scripts should know the storage backend.

## SQLite Store

`scripts/sqlite-store.py` can export JSON stores into SQLite or restore JSON from SQLite:

```bash
python3 scripts/sqlite-store.py export --db data/fluent.sqlite
python3 scripts/sqlite-store.py import --db data/fluent.sqlite --output-dir data-restored
```

It writes:

- `documents` - exact logical store documents
- `review_items` - normalized spaced-repetition items
- `sessions` - normalized session-log entries
- `error_patterns` - normalized mistake patterns
- `metadata` - backend metadata

SQL mode also writes JSON mirrors by default for compatibility and easier inspection.
