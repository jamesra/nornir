# RC2 Grid16 605-606 refine performance

## Decision

Keep `NORNIR_REFINE_FINALIZED_RECHECK_MODE=all` as the production default. The
`local` candidate preserved quality exactly, but failed the runtime acceptance
criterion and is therefore not enabled by default.

## Repeated benchmark

All timed code runs used the Automatic 605-606 STOS input. Each variant used one
warm-up followed by three measured runs. Quality used the fixed control-space
Grid16 lattice (cell 256, spacing 192).

- Current trusted mesh: 46.589, 57.371, and 50.062 seconds; median 50.062 seconds.
- Final local candidate: 91.439, 73.020, and 63.385 seconds; median 73.020 seconds.
- Runtime change: 45.9% slower. Required acceptance: at least 20% faster.
- Current and local output SHA-256 values were identical in every retained run:
  `c04f0d44b8ee2b3d5cadac3c96a4ef5b1aed2ec1ea22414ca02f28ab49c25933`.

## Quality acceptance

- Evaluated cells: 1,136 in both variants.
- Improved/worse/unchanged: 0 / 0 / 1,136 at the `1e-4` threshold.
- Cell ZNCC median/minimum/maximum: 0.4153178600 / 0.2296912782 / 0.7578918096.
- Full-pair ZNCC: 0.4444788710.
- Every paired cell delta was exactly zero.

The local rule skipped only two of 3,332 finalized rechecks. Shadow evidence
showed neither would have produced an accepted improvement, but this amount of
avoided work cannot offset the local-geometry bookkeeping. The safety-pair gate
for making local the default was not entered because 605-606 failed the runtime
gate.

## Verification

- Focused scheduling/scoring suite: 50 passed.
- Headless refine regression assertions: 174 passed, 1 skipped, 13 subtests
  passed.
- The broader pytest command returned nonzero only during teardown after its
  process-leak guard killed two multiprocessing helper processes.

See `report.json` for aggregate data and the CSV/PNG files in this directory for
paired-cell distributions and spatial heatmaps. Large run outputs and manifests
remain under `/tmp/nornir-test-output/rc2-605-performance`.
