---
name: refine-grid-trust-review
description: >-
  Reviews or designs refine-grid (STOS local distortion correction) changes against
  the trust principle: names the trust question, checks for untrusted cells in
  the mesh, requires relative constants and pair-based evidence. Use when editing
  local_distortion_correction.py or refine_shared, adding a gate or threshold to
  grid refine, or investigating a refine result that jumped, froze, or returned
  the input unchanged.
---

# Refine-grid trust review

Paired rule: [`.cursor/rules/Refine-grid-trust-questions.mdc`](../../rules/Refine-grid-trust-questions.mdc).

Inventory (current steps, flow, trust questions):
[`nornir-imageregistration/docs/refine_grid_step_inventory.md`](../../../nornir-imageregistration/docs/refine_grid_step_inventory.md).

**Principle:** only trusted cells shape the field. A cell is trusted when its
own measurement is unique (`peak_ratio`) and prominent (ZNCC) **and** it agrees
with trusted neighbours or converges under the field it helped build. Untrusted
cells never enter the mesh; where nothing is trusted the input transform stands.

## Checklist

Copy and fill this before editing:

```
Trust review:
- [ ] Step 1: located in inventory flow (step # / branch)
- [ ] Step 2: three trust-question answers written
- [ ] Step 3: mesh membership path checked for untrusted records
- [ ] Step 4: motivating pair + healthy pair; metrics to report
- [ ] Inventory updated if a step is added or removed
```

## Step 1 — Locate the change in the inventory flow

Read the inventory mermaid (section 1) and the numbered table (section 2).
Name the step number, module, and branch (`Track A`, `Track B`, roles, ZNCC,
best_effort, anchor-smooth, travel filter, `_build_mesh_transform_or_keep`,
sparse-mesh preserve, finalize).

If the change is a new step, say where it sits in that flow **before** writing
code. If a step is added or removed, update the inventory in the same change.

## Step 2 — Three trust-question answers

Write these in the plan or commit message:

1. **Trust question** (exactly one):
   - "is there tissue to measure"
   - "is this peak unique"
   - "does this peak beat its local null"
   - "does this cell agree with trusted neighbours"
   - "has this cell converged under the current field"
   - "is there anything trusted at all (seeding)"
2. **Existing step** that already answers it (inventory #).
3. **Why that answer is insufficient**, with a measurement from a **named pair**.

If the honest answer to (1) is "the mesh contains untrusted cells and this change
limits the damage", **stop**. Fix mesh membership instead. That is the retired
pattern: global residual translation applied without a uniqueness gate;
sparse-mesh preserve with absolute floors; anchor-smooth with raw-preserve;
best-effort promotion of ambiguous peaks; field-level branding modes.

Constants must be relative (fraction of `n_grid`, quantile of the pass
distribution, multiple of `max_travel` or cell size), never absolute counts.
State the pair and the measured distribution that set any new constant.

## Step 3 — Mesh membership path

Grep `_build_mesh_transform_or_keep` in
`nornir_imageregistration/local_distortion_correction.py`. Today there are two
callers in the per-pass loop:

| Path | How records reach the mesh |
|------|----------------------------|
| Anchor-smooth | `smooth_peaks_from_locked_anchors` then `_build_mesh_transform_or_keep` (no `fixed_points`). Raw-preserve IDs keep unvetted peaks. |
| Travel / REJECT filter | `filter_records_for_mesh_inclusion` then `exclude_reject_mesh_records` (`min_keep=0`), then `_build_mesh_transform_or_keep` with locked `fixed_points`. |

After either caller, `should_keep_prior_sparse_mesh` may discard the mesh and
log `Keeping prior transform`.

Ask: **how could an untrusted record reach `_build_mesh_transform_or_keep`?**
Typical leaks: best-effort promotion of ambiguous peaks into FREE; raw-preserve
on disc / unique-large / coherent-front cells; relaxed travel limits; Track A/B
`TranslateFixed` that moves the whole field without a uniqueness gate. If the
change only "limits the damage" of those records, reject it.

Fewer than three points keeps the prior transform (`Insufficient points for mesh
update`). That is correct when nothing is trusted; do not emergency-fill with
rejects.

## Step 4 — Fixture pairs and metrics

Verify on **at least one pair that motivated an existing mechanism** plus
**one healthy pair**. A change that lowers the healthy pair's lock fraction is
not accepted.

| Pair | Why it exists (inventory) |
|------|---------------------------|
| RC2 Grid16 **1215-1214** | Track B jump (`peak_ratio=0.95`); then sparse-preserve no-op at 512 |
| **240-241** | Track A / whole-FOV residual; preserve absolute floor |
| **241-242** | Asymmetric / identity bubble; field branding |
| **252-254** | Disc-front feedback (78 → 489) |
| **953-952** | best_effort promotion of weak peaks |
| **228-229** | Travel filter vs weight-only mesh inclusion |
| Healthy Grid16 (e.g. **183-184**, **242-243**) | Lock fraction must not drop (baseline ~29–36%) |

**Report both:**

- **lock fraction** — final `len(finalized_points) / n_grid` (and per-pass)
- **unique-fraction-over-passes** — unique peaks / `n_grid` each pass (do not
  collapse to a single end-of-run number)

Healthy Grid16 pairs settle near ~31% locks; see
[`grid16_rc2_refine_baseline.md`](../../../nornir-imageregistration/docs/grid16_rc2_refine_baseline.md).

## Step 5 — Reconstruct a Pyre run from the console log

Search the session log under `NORNIR_LOG_ROOT` (not ad hoc files) for:

| Log fragment | Meaning |
|--------------|---------|
| `Pass N aligned` | Measurement count this pass (`after residual revert` if Track A/B was undone) |
| `Coherent residual translation:` / `Coherent residual skipped:` | Track A; includes `n_unique=`, `n_inliers=`, `coherence=` |
| `Global FOV residual translation:` / `Global FOV residual skipped:` | Track B; skipped lines name `n_unique=0` or `no usable peak` |
| `field_mode=` | Roles: `reject=` `free=` `lockable=` `peak_amb=` `zncc_pass=` `zncc_fail=` `best_effort=` |
| `Anchor-smooth mesh:` | Lock seeds vs cells in smoothed field, `raw-preserve=` |
| `points included in updated transform` | Records that actually entered `_PeakListToTransform` |
| `Keeping prior transform` | Sparse-mesh preserve or insufficient points; output stays the input field |
| `has locked` | `Pass N has locked X new points ... Y of Z are locked` |

Also useful: `Reverted residual translation after remeasure`,
`Dropped N REJECT free points from mesh inclusion`,
`Dropped N free points from mesh inclusion (peak travel`.

Unique fraction ≈ `n_unique / n_grid` from the residual lines, or
`(n_grid - peak_amb) / n_grid` from `field_mode=` (same pass). Lock fraction is
the `Y of Z are locked` ratio.

## Worked example — RC2 Grid16 1215-1214

Track B applied a whole-FOV translation with `peak_ratio=0.95`.

| Answer | Content |
|--------|---------|
| Trust question | "is there anything trusted at all (seeding)" |
| Existing step | Track A (inventory #7); Track B was the fallback when Track A skipped |
| Insufficient because | Track B had no uniqueness gate. On 1215-1214 it accepted a `peak_ratio=0.95` peak of 2654–3510 px and the section jumped. |
| Immediate fix | Gate Track B on `PEAK_RATIO_MIN` so a non-unique whole-FOV peak cannot `TranslateFixed`. |
| Longer-term fix | Mesh membership: untrusted cells never enter the mesh; with 0 locks the input transform stands. Sparse-preserve with `MIN_MESH_ABS_AFTER_RESIDUAL=100` then made the 79-cell 512 run a no-op — another "limit the damage" patch, not a trust gate. |
