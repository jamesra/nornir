---
name: archive-built-plans
description: Archives completed Cursor agent plan files into `.cursor/Built Plans/`, updates the deliverables index, and leaves active plans in `.cursor/plans/`. Use when a plan is fully built, todos are all completed, or the user asks to move or archive built plans.
---

# Archive Built Plans

## Layout

| Location | Purpose |
|----------|---------|
| `.cursor/plans/` | Active / in-progress plans (workspace) |
| `.cursor/Built Plans/` | Fully completed plans (archive) |
| `.cursor/Built Plans/README.md` | Deliverables index — **update when archiving** |
| `.cursor/plans/README.md` | Points to archive; lists active plans |

Plan **deliverables** (code, rules, docs under `docs/`, package READMEs) stay in their normal paths. Only the `.plan.md` file moves.

Plans may also exist outside the repo in the Cursor IDE plans directory (e.g. `~/.cursor/plans/`). Move those into `.cursor/Built Plans/` when fully built so they are version-controlled with the monorepo.

## When a plan is "built"

A plan is ready to archive when **every todo in its YAML frontmatter is `status: completed`** and there are **no** `pending` or `in_progress` todos.

Do **not** archive if:
- Any todo is `pending` or `in_progress`
- Todos list is empty and work was never tracked (treat as open unless the user confirms completion)
- The user explicitly says the plan is still active

## Workflow

```
Task Progress:
- [ ] Find candidate plan files (*.plan.md)
- [ ] Classify built vs open (todo statuses)
- [ ] Document deliverables in Built Plans README (if new row needed)
- [ ] Move built plans to `.cursor/Built Plans/`
- [ ] Update `.cursor/plans/README.md` active table
- [ ] Verify no duplicate filenames in destination
```

### Step 1 — Classify plans

Scan `.cursor/plans/` and, if relevant, the Cursor IDE plans directory for `*.plan.md`.

Parse frontmatter todo lines: `status: completed|pending|in_progress|cancelled`.

**Built:** at least one `completed` todo and zero `pending` / `in_progress`.

Quick check (adjust paths as needed):

```bash
python3 <<'PY'
import re, pathlib
for p in sorted(pathlib.Path(".cursor/plans").glob("*.plan.md")):
    statuses = re.findall(r"status:\s*(\w+)", p.read_text())
    if not statuses:
        print(f"NO_TODOS\t{p.name}")
    elif any(s in ("pending", "in_progress") for s in statuses):
        print(f"OPEN\t{p.name}")
    elif any(s == "completed" for s in statuses):
        print(f"BUILT\t{p.name}")
PY
```

Also check `~/.cursor/plans/*.plan.md` when the user mentions IDE plans outside the workspace.

### Step 2 — Document before moving

For each newly archived plan, add a row to `.cursor/Built Plans/README.md`:

| Plan | Primary deliverables |

Deliverables = concrete paths (pipelines, modules, tests, rules, scripts, docs). One line per plan; link the plan filename.

Remove the plan from the "Plans still open" section of that README if it was listed there.

Update `.cursor/plans/README.md`: remove archived entries from the active table; add a row only for plans still in `.cursor/plans/`.

Do **not** edit plan file bodies unless the user asks — frontmatter and notes are historical record.

### Step 3 — Move files

```bash
mkdir -p ".cursor/Built Plans"
mv ".cursor/plans/<name>.plan.md" ".cursor/Built Plans/"
# repeat for each built plan; same for ~/.cursor/plans/ when applicable
```

Use `mv`, not copy-only, to avoid duplicates.

### Step 4 — Verify

- `.cursor/Built Plans/` contains the moved files + README
- `.cursor/plans/` holds only active plans (+ its README)
- Every new archive row in Built Plans README has deliverable paths that exist in the repo

## Examples

**Archive after finishing a feature plan**

1. Confirm all todos `completed` in `pipeline_command_chaining_b922dc68.plan.md`
2. Add row: chaining → `build.py --then`, `tests/pipeline/test_chain.py`, `TEMBuild.cmd`
3. Move file to `.cursor/Built Plans/`
4. Remove from active table in `.cursor/plans/README.md`

**Partial plan — do not archive**

`fix_grid690_python_parity.plan.md` has pending todos → stays in `.cursor/plans/` even if Phase 0 docs exist at `docs/refine-grid-cpp-parity-checklist.md`.

**Batch archive**

User says "move all built plans": classify all candidates, update README once with all new rows, then move all built files in one pass.

## Anti-patterns

- Moving deliverable `.md` files (checklists, assessment reports) into Built Plans — those belong in `docs/` or package trees
- Archiving plans with open todos
- Editing archived plan files to mark todos complete retroactively
- Creating the archive outside `.cursor/Built Plans/` without user request
