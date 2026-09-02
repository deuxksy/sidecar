# Agent Instructions

> Before starting work, read and strictly follow the root rules in `.ai/RULES.md`.

## Codex & General Agent Workflow
1. Read `.ai/RULES.md` for architecture, wire protocol constraints, and hardware gotchas.
2. Run tests via `uv run pytest` after modifying Python source code.
3. Preserve layout data separation: protocol changes belong in `layout.json`, not hardcoded in Python logic.
