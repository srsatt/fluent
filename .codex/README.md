# Codex Harness

This folder contains Codex-specific entry points for Fluent.

Shared assets are symlinked:

- `skills -> ../skills`
- `scripts -> ../scripts`

Codex should read the repository-level `AGENTS.md`, then `TUTOR.md`, then the relevant `skills/<skill>/SKILL.md` file for each `/fluent-*` learner command.

Use `rtk` when running shell commands in this repo.
