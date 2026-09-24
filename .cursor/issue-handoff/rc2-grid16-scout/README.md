# RC2 Grid16 refinement scout

Resumable command:

```text
NORNIR_HEADLESS=1 nornir-stos-group-scout \
  --group /storage4/RC2/TEM/Grid16 \
  --limit 50 \
  --output-dir $TESTOUTPUTPATH/refine_group_scout/Grid16
```

The live checkpoint and trial outputs stay under `TESTOUTPUTPATH/refine_group_scout/Grid16` (`scout.sqlite`, per-pair scratch `.stos`). This folder keeps the ranking reports only.

## Result

- Inventoried 1,306 group-root transforms; excluded Manual pairs; screened the 50 lowest cached pair-ZNCC files.
- Trialed two scratch schedules from the current group-root transform: dense 256/128 and fine 128/64, 10 iterations each.
- Scored on a full-resolution 128-cell lattice. 39 pairs accepted, 11 rejected for quality-flag (low final lock fraction). No trial errors.
- Preferred schedule among accepted pairs: 23 fine128, 16 dense256.

Priority CSV is ordered by repaired weak-cell clusters, then net improved cells, lower-tail and median cell delta, then pair ZNCC delta.
