---
name: nornir-realworld-refine-benchmark
description: >-
  Benchmarks and A/B-tests refine-grid (RefineStosFile / local_distortion_correction)
  changes on real RC2 section pairs: fixture semantics (Automatic input vs Manual
  gold), the refine fixture catalog, the repeated-run baseline runner, the
  per-cell ZNCC analysis script, and the acceptance bar for speed and quality.
  Use when a change could alter refine-grid runtime or output, when building or
  reading refine fixtures, or when asked whether a refine optimization is faster.
---

# Real-world refine-grid benchmark

Paired rules: [Performance-evidence](../../rules/Performance-evidence.mdc) (no claim without a
measured number) and [Refine-grid-trust-questions](../../rules/Refine-grid-trust-questions.mdc)
(quality changes). Trust review procedure and fixture pair roles:
[refine-grid-trust-review](../refine-grid-trust-review/SKILL.md).

## Fixture semantics

Fixtures: `$TESTINPUTPATH/refine_fixtures/<volume>/<group>/<pair>/` (Windows host:
`D:/nornir-testdata/refine_fixtures/`; container: `/nornir-testdata/refine_fixtures/`).

| File | Meaning |
|------|---------|
| `input.stos` | **Automatic** product: what refine would have been given |
| `gold.stos` | Unsuffixed **Manual** Leveled transform; the reference, never an input |
| `control.png` / `mapped.png` (+ `_mask`) | Leveled images for the pair |
| `manifest.json` | `input_kind`, `input_note`, `gold_kind`, `source_stos` + checksum, tags, `bbox_yxhw` |

- **Never use the Grid16 group-root `.stos` as input**: for Manual pairs the pipeline copies Manual
  over the group root and deletes `Grid16/Automatic/`, so the group root is already gold.
- Manual variants (`-Rigid`, `-Mesh`) are not gold.
- If `Grid16/Automatic/<pair>_...Leveled.stos` is gone, rebuild the Automatic input from the
  **Grid32** group root with `StosFile.ChangeTransformPixelSpacing(oldspacing=32, newspacing=16)`,
  then rewrite image paths to Grid16 Leveled (manifest: `input_kind: grid32_scaled_to_ds16`). No
  script does this; do it ad hoc and pass the result to
  `nornir-import-refine-fixture --stos <rebuilt> --manual <Manual gold>`.
- Pair lists and tags: [rc2-grid16-refine-fixtures.md](../../issue-handoff/rc2-grid16-refine-fixtures.md),
  [rc2-grid32-refine-fixtures.md](../../issue-handoff/rc2-grid32-refine-fixtures.md).

## Catalog

`D:/nornir-testdata/refine_fixtures/catalog.sqlite` (`refine_assessment.catalog.catalog_path`:
`<fixtures-root>/catalog.sqlite`). Entry points from `nornir-imageregistration`:

| Command | Use |
|---------|-----|
| `nornir-import-refine-fixture` | Add a fixture (`--stos`, `--manual`, `--from-manual-dir`, `--volume`, `--group`, `--pair`, `--tags`) |
| `nornir-tag-fixture` | Confirm tags in the catalog |
| `nornir-ab-refine-fixtures` | Refine each fixture's `input.stos` and score vs gold (`--fixture <rel-dir>` repeatable, `--tag`, `--work-dir`, `--iterations`, default 3) |
| `nornir-stos-group-scout` | Rank non-Manual pairs in a live group for refine trials (see `rc2-grid16-scout/README.md`) |

Run A/B against fixtures, never against the live volume.

## Baseline runner (runtime and trust metrics)

[`run_refine_grid_baseline.py`](../../issue-handoff/run_refine_grid_baseline.py) runs `RefineStosFile`
with Grid16 production settings (cell 256, spacing 192, 10 iterations), writes
`$TESTOUTPUTPATH/refine_grid_baseline_<variant>/manifest.json` plus per-pair `summary.json` (wall time,
output SHA-256, per-pass lock/unique fractions, phase totals, control-point deltas, ZNCC), and records
the package Git SHA and diff hash. Environment variables:

| Variable | Effect |
|----------|--------|
| `NORNIR_REFINE_BASELINE_VARIANT` | Output folder suffix; use one per run (`current-measured-1`, ...) |
| `NORNIR_REFINE_BASELINE_PAIRS` | Comma list, e.g. `605-606`; default all pairs in `PAIRS` |
| `NORNIR_REFINE_BENCHMARK_RUN_KIND` / `_REPETITION` | Recorded in the manifest (warm-up vs measured) |
| `NORNIR_REFINE_PHASE_TIMING` | Defaults to 1; set `0` for timed runs |
| `NORNIR_REFINE_FINALIZED_RECHECK_MODE` | `all` (default), `shadow`, `local` |

Caveats:

- Inputs are read from the live volume path `GRID16 = /storage4/RC2/TEM/Grid16` (container); edit it
  on the Windows host.
- `manual` entries (1215-1214, 240-241) feed Manual as input, and `automatic` falls back to the group
  root when `Automatic/` is missing. So the runner answers "what does refine do to what the pipeline
  consumes", not "how close to gold"; for gold scoring use `nornir-ab-refine-fixtures`.
- `605-606` uses `automatic-strict` (no fallback) and is the timing pair.

Protocol: same machine and session, idle; **one warm-up then three measured runs per variant**;
compare medians. Point `TESTOUTPUTPATH` at one benchmark root (e.g. `.../rc2-605-performance`).

## Analysis script

[`analyze_refine_grid_performance.py`](../../issue-handoff/analyze_refine_grid_performance.py) scores
each run on the fixed control-space lattice (cell 256, spacing 192) and writes per-variant summaries,
per-cell delta CSV, histogram/ECDF and spatial heatmap PNGs, and `report.json`:

```text
python analyze_refine_grid_performance.py \
  --benchmark-root $TESTOUTPUTPATH/rc2-605-performance \
  --output-dir <report dir> \
  --production-stos <volume group-root .stos for the pair (reference score only)> \
  --pair 605-606 \
  --group current=refine_grid_baseline_current-measured-* \
  --group candidate=refine_grid_baseline_candidate-measured-* \
  --compare current:candidate
```

`--group LABEL=GLOB` matches `<benchmark-root>/<GLOB>/manifest.json`; `--compare REF:CAND` is repeatable
and may use `production`. Worked example: [rc2-605-performance-final/](../../issue-handoff/rc2-605-performance-final/README.md).

## Acceptance criteria

- **Runtime:** candidate median at least **20% faster** than current on 605-606.
- **Output:** for a behaviour-preserving change, output SHA-256 identical in every retained run.
- **Quality:** per-cell ZNCC deltas at tolerance `1e-4` reported as improved / worse / unchanged,
  with distribution and heatmap; any worse cells need a trust-rule justification.
- **Trust metrics:** lock fraction and unique-fraction-over-passes on a motivating pair plus a healthy
  pair; a lower healthy-pair lock fraction is not accepted.
- A runtime failure ends the evaluation; the safety-pair gate is not entered.

Standing decision: keep **`NORNIR_REFINE_FINALIZED_RECHECK_MODE=all`** as the production default. The
`local` candidate kept output bit-identical but was 45.9% slower (median 73.0 s vs 50.1 s). Rejected
refine candidates are logged in [optimization-loop-rejections.md](../../issue-handoff/optimization-loop-rejections.md).
