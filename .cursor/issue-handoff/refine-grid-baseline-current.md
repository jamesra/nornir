# Refine-grid current-path baseline (2026-09-16)

Current-code A/B reference for the trusted-mesh plan. Artifacts are under `TESTOUTPUTPATH`, not the volume.

- **Runner:** `.cursor/issue-handoff/run_refine_grid_baseline.py` (`RefineStosFile`, Grid16 production settings)
- **Output:** `/tmp/nornir-test-output/refine_grid_baseline_current/`
  - `manifest.json` — all pairs
  - `<pair>/summary.json`, `<pair>/<pair>_refined.stos`
  - `<pair>/refine_diagnostics/<pair>_refined/refine_passNN_diagnostics.{npz,csv}`
  - `runner.log`
- **Settings:** cell 256, spacing 192, 10 iterations, `NORNIR_HEADLESS=1`, `NORNIR_REFINE_PASS_DIAGNOSTICS=1`, `NORNIR_REFINE_PHASE_TIMING=1`
- **Uniqueness bar:** `PEAK_RATIO_MIN = 1.20`
- **Created:** 2026-09-16T01:41:01Z (session log `/.nornir-logs/2026-09-16/nornir-session-20260916-014101.log`)

Inputs were the pre-refine STOS the pipeline would consume (Manual when present, else Automatic). Volume `Grid16/*.stos` products were not overwritten.

## Headline metrics

| Pair | Role | Input | Wall s | Passes | Lock p1→last | Unique p1→last | CP RMS / med / max px | quality_flag |
|------|------|-------|--------|--------|--------------|----------------|------------------------|--------------|
| 1215-1214 | challenging-band | Manual | 94.9 | 10 | 0.312 → 0.841 | 0.949 → 0.981 | 36.63 / 2.04 / 243.04 | false |
| 240-241 | challenging-coherent-residual | Manual | 52.2 | 2 | 0.952 → 0.962 | 0.985 → 0.994 | 11.12 / 1.80 / 103.23 | false |
| 241-242 | challenging-identity-bubble | Automatic | 137.5 | 10 | 0.038 → 0.291 | 0.403 → 0.609 | 127.55 / 85.95 / 459.60 | false |
| 252-254 | challenging-tear-front | Automatic | 38.7 | 3 | 0.635 → 0.922 | 0.973 → 0.987 | 15.94 / 9.89 / 63.92 | false |
| 228-229 | challenging-high-weight-outliers | Automatic | 57.0 | 3 | 0.555 → 0.961 | 0.976 → 0.998 | 38.22 / 15.76 / 161.80 | false |
| 953-952 | challenging-subpar | Automatic | 103.6 | 10 | 0.368 → 0.818 | 0.675 → 0.928 | 121.94 / 23.96 / 529.12 | false |
| 183-184 | healthy | Automatic | 141.1 | 10 | 0.292 → 0.823 | 0.877 → 0.908 | 35.76 / 12.05 / 223.07 | false |

Control-point deltas compare the refined grid’s source points through the **input** vs **output** transforms.

## Observations for A/B

- **241-242** is the weak pair: last lock 29%, unique 61%, discontinuities rise 807 → 674, CP median 86 px. Quality flag still false.
- **953-952** finishes with decent lock (82%) but large CP motion (RMS 122, max 529).
- **240-241 / 252-254 / 228-229** early-exit after 2–3 passes with lock ≥ 0.92.
- **183-184** (healthy) still runs all 10 passes; last unique among unlocked is only 0.48.
- Repeat the same runner after trusted-mesh lands; keep this directory as the “A” side.

## Repeat

```bash
NORNIR_HEADLESS=1 /opt/venv/bin/python3 /workspace/.cursor/issue-handoff/run_refine_grid_baseline.py
```

Change the output folder name (or add a flag) before the B run so this tree is not overwritten.

## Trusted-mesh result

The final pre-retirement B artifacts are in
`/tmp/nornir-test-output/refine_grid_baseline_trusted_mesh_final/`;
`ab_comparison.json` contains complete lock and uniqueness series.

| Pair | Final lock A→B | Final unique A→B | Pair ZNCC A→B |
|------|----------------|------------------|---------------|
| 1215-1214 | 0.841 → 0.962 | 0.981 → 0.996 | 0.0464 → 0.0457 |
| 240-241 | 0.962 → 0.997 | 0.994 → 0.999 | 0.5821 → 0.5791 |
| 241-242 | 0.291 → 0.999 | 0.609 → 0.999 | 0.5210 → 0.6651 |
| 252-254 | 0.922 → 0.992 | 0.987 → 0.999 | 0.4860 → 0.4810 |
| 228-229 | 0.961 → 0.994 | 0.998 → 0.999 | 0.6839 → 0.6843 |
| 953-952 | 0.818 → 0.978 | 0.928 → 0.991 | 0.1194 → 0.1202 |
| 183-184 | 0.823 → 0.993 | 0.908 → 0.997 | 0.2337 → 0.2286 |

Post-retirement validation used 241-242 and healthy 183-184. Their final
lock/unique fractions were 0.999/0.999 and 0.996/0.998 respectively, so removing
the proxy branches and final nudge did not lower the healthy acceptance metrics.
Artifacts are in
`/tmp/nornir-test-output/refine_grid_baseline_retired_validation/`.

Post-audit validation after preserving coherent no-lock cluster seeds used the
same two pairs. Final lock/unique fractions were 0.999/0.999 for 241-242 and
0.996/0.998 for healthy 183-184 (rounded to three decimals), matching the
post-retirement acceptance metrics. Artifacts are in
`/tmp/nornir-test-output/refine_grid_baseline_post_audit_cluster_seed/`.
