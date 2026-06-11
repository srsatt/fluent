@../AGENTS.md

# Codex Harness Notes

This folder is only harness-specific glue. The canonical tutor instructions live in `../TUTOR.md`; shared skills and scripts live in `../skills` and `../scripts`.

For practice sessions:

```bash
rtk python3 scripts/read-db.py
rtk python3 scripts/update-db.py
```

Storage defaults to SQL through `../.env`:

```dotenv
db=sql
```
