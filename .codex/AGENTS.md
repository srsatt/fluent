@../AGENTS.md

# Codex Harness Notes

This folder is only harness-specific glue. The canonical tutor instructions live in `../TUTOR.md`; shared skills and scripts live in `../skills` and `../scripts`.

Fluent-only checkout rule: use only `../skills/fluent-*` skill files for learner commands and the repo-local `fluent` MCP server for persistence. Do not load repo-local `.agents` skills, unrelated MCP servers, or non-Fluent plugin/tool configuration from this repository.

For practice sessions:

```text
fluent_read_state
fluent_update_session
fluent_score_to_quality
```

Use `rtk python3 scripts/read-db.py` and `rtk python3 scripts/update-db.py` only as fallback when MCP is unavailable.

Storage defaults to SQL through `../.env`:

```dotenv
db=sql
```
