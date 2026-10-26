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

Only the `.plan.md` file moves. Deliverables (code, rules, `docs/`, package READMEs) stay where they are;
never move deliverable `.md` files (checklists, assessment reports) into Built Plans.

Plans in the Cursor IDE plans directory (e.g. `~/.cursor/plans/`) also move into `.cursor/Built Plans/`
when fully built, so they are version-controlled with the monorepo. Check `~/.cursor/plans/*.plan.md`
when the user mentions IDE plans outside the workspace.

## When a plan is "built"

Its YAML frontmatter todos have at least one `completed` and zero `pending` / `in_progress`
(`cancelled` todos do not block archiving; this is what the check below tests).

Do **not** archive if:
- any todo is `pending` or `in_progress`;
- the todo list is empty and work was never tracked (open unless the user confirms completion);
- the user says the plan is still active.

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

### 1. Classify

Scan `.cursor/plans/` (and the IDE plans directory if relevant) for `*.plan.md`; parse frontmatter
`status: completed|pending|in_progress|cancelled`. Quick check (adjust paths):

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

### 2. Document before moving

- Add a row per newly archived plan to `.cursor/Built Plans/README.md` (`| Plan | Primary deliverables |`):
  link the plan filename; list concrete deliverable paths (pipelines, modules, tests, rules, scripts,
  docs) that exist (check with Glob). One line per plan.
- Remove the plan from that README's "Plans still open" section if listed.
- In `.cursor/plans/README.md`, remove archived entries from the active table; rows only for plans
  still in `.cursor/plans/`.
- Do **not** edit plan file bodies unless asked; frontmatter and notes are historical record (never
  mark todos complete retroactively).

### 3. Move

```bash
mkdir -p ".cursor/Built Plans"
mv ".cursor/plans/<name>.plan.md" ".cursor/Built Plans/"
# repeat for each built plan; same for ~/.cursor/plans/ when applicable
```

Use `mv`, not copy, to avoid duplicates. Do not create the archive outside `.cursor/Built Plans/`
without a user request.

### 4. Verify

- `.cursor/Built Plans/` contains the moved files + README.
- `.cursor/plans/` holds only active plans (+ its README).
- Every new archive row's deliverable paths exist in the repo.

## Examples

- **Finished feature plan:** all todos `completed` in `pipeline_command_chaining_b922dc68.plan.md` →
  add row: chaining → `build.py --then`, `nornir-buildmanager/scripts/TEMBuild.cmd` → move to
  `.cursor/Built Plans/` → remove from the active table in `.cursor/plans/README.md`.
- **Partial plan:** `fix_grid690_python_parity.plan.md` has pending todos, so it stays in
  `.cursor/plans/` even though Phase 0 docs exist at `docs/refine-grid-cpp-parity-checklist.md`.
- **Batch ("move all built plans"):** classify all candidates, update the README once with all new
  rows, then move all built files in one pass.
