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

## Glob-scoped rules

Claude Code does not read `.cursor/rules/` frontmatter on its own. Before editing files
that match a scope in the "Glob-scoped" table in AGENTS.md, read that rule file
(e.g. `.cursor/rules/python-standards.mdc` before any `*.py` edit,
`.cursor/rules/Numpy-CuPy-compatibility.mdc` before touching `nornir-imageregistration`).
Treat their "must not" / "do not" items as non-negotiable, per Design-choice-confirmation.

## Skills

Procedures live in `.cursor/skills/*/SKILL.md` (catalog: `.cursor/skills/README.md`).
When a task matches a skill's "when to use" line in AGENTS.md, read that SKILL.md first.

## Commands (Windows, from the repo root)

- Python: `venv\pyre314\Scripts\python.exe`
- Tests: `venv\pyre314\Scripts\pytest.exe` (testpaths and pythonpath are set in `pytest.ini`)
  - Headless / fast: `-m "not graphical and not slow and not gpu and not needs_data"`
  - External test data setup: see `TEST_DATA_SETUP.md`
- Lint: `venv\pyre314\Scripts\ruff.exe check <path>`
- Types: `venv\pyre314\Scripts\pyright.exe` (config: `pyrightconfig.json`, basic mode)

## Housekeeping

- Do not write scratch notes, test output, `debug-*.log`, or `pyright_*.json` dumps to the repo root.
  Notes go in `.cursor/issue-handoff/`, test artifacts under `TESTOUTPUTPATH`, logs under `NORNIR_LOG_ROOT`.
- Submodule edits: commit inside the submodule, then bump the umbrella pointer and check
  `git submodule status` shows no `+` lines.
