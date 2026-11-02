# Nornir — Claude Code instructions

Umbrella repo for the `nornir-*` packages (plus `dm4`), each a git submodule.
The canonical agent guidance is shared with Cursor and lives in `AGENTS.md` and
`.cursor/rules/`. This file only pulls it in for Claude Code; edit the rules there,
not here.

## Project index

@AGENTS.md

## Always-applied rules (loaded in full)

@.cursor/rules/Virtual-Env.mdc
@.cursor/rules/Design-choice-confirmation.mdc
@.cursor/rules/Unified-Logging-Convention.mdc
@.cursor/rules/Monorepo-submodule-changes.mdc
@.cursor/rules/Shared-checkout-safety.mdc
@.cursor/rules/Line-endings-and-encoding.mdc
@.cursor/rules/Workspace-map.mdc
@.cursor/rules/Questions-and-proving-fixes.mdc
@.cursor/rules/user-changelog.mdc

## Glob-scoped rules

Claude Code does not read `.cursor/rules/` frontmatter. `.claude/sync_claude_rules.py` mirrors
every glob-scoped rule into `.claude/rules/<name>.md` with a `paths:` list, so Claude loads it
when it reads or edits a matching file. After adding or editing a `.cursor/rules/*.mdc`, run
`venv\pyre314\Scripts\python.exe .claude\sync_claude_rules.py` (`--check` reports drift and
always-applied rules missing from this file). Never edit `.claude/rules/` by hand.
Treat their "must not" / "do not" items as non-negotiable, per Design-choice-confirmation.

## Skills

Procedures live in `.cursor/skills/*/SKILL.md` (catalog: `.cursor/skills/README.md`).
When a task matches a skill's "when to use" line in AGENTS.md, read that SKILL.md first.

## Commands (Windows, from the repo root)

- Python: `venv\pyre314\Scripts\python.exe`
- Tests: `venv\pyre314\Scripts\pytest.exe` (testpaths and pythonpath are set in `pytest.ini`)
  - Headless / fast: `-m "not graphical and not slow and not gpu and not needs_data"`
  - External test data setup: see `TEST_DATA_SETUP.md`
  - Known flaky / baseline failures and lint-delta checks: `nornir-verify-change` skill
- Lint: `venv\pyre314\Scripts\ruff.exe check <path>`
- Types: `venv\pyre314\Scripts\pyright.exe` (config: `pyrightconfig.json`, basic mode)

## Housekeeping

- Do not write scratch notes, test output, `debug-*.log`, or `pyright_*.json` dumps to the repo root.
  Notes go in `.cursor/issue-handoff/`, test artifacts under `TESTOUTPUTPATH`, logs under `NORNIR_LOG_ROOT`.
- Submodule edits: commit inside the submodule, then bump the umbrella pointer and check
  `git submodule status` shows no `+` lines. Full commit/push order: `nornir-commit-push` skill.
