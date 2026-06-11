# Codex Harness

This folder contains Codex-specific entry points for Fluent.

Shared assets are symlinked:

- `skills -> ../skills`
- `scripts -> ../scripts`

Codex should read the repository-level `AGENTS.md`, then `TUTOR.md`, then the relevant `skills/<skill>/SKILL.md` file for each `/fluent-*` learner command.

Use the repo-local Fluent MCP tools for persistence when available: `fluent_read_state`, `fluent_update_session`, and `fluent_score_to_quality`. Use `rtk` when running shell fallback commands in this repo.

This checkout is intended to stay Fluent-only: do not add copied `.agents/skills` trees, non-Fluent skills, or non-Fluent MCP server configuration.
