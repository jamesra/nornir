# Optimization loop rejections

## Duplicate rigid-ring center transform

- Date: 2026-09-16
- Package: `nornir-imageregistration`
- Candidate: In `ApproximateRigidTransformBySourcePoints`, reuse
  `target_rings[:, 0, :]` instead of separately transforming every source center.
- Benchmark: RC2 Grid16 605-606, finalized recheck mode `all`, phase timing off,
  one warm-up plus three measured runs.
- Baseline: 52.937, 49.838, 40.135 seconds; median 49.838 seconds.
- Candidate: 45.767, 56.376, 56.268 seconds; median 56.268 seconds.
- Result: Rejected and reverted. The candidate was 12.9% slower by measured
  median despite eliminating one transform call per point setup.
- Quality: Every retained output had SHA-256
  `c04f0d44b8ee2b3d5cadac3c96a4ef5b1aed2ec1ea22414ca02f28ab49c25933`.
- Do not retry based only on transform-call counts. Any future reconsideration
  needs isolated transform microprofiling that explains why the removed call
  improves end-to-end wall time despite this result.

## Join XML string fragments

- Date: 2026-09-16
- Package: `nornir-buildmanager`
- Candidate: Replace the loop in `XElementWrapper.__str__` with `str.join`.
- Benchmark: Median of five conversions of wrappers containing 1,000, 5,000,
  and 10,000 child elements.
- Baseline at 10,000 children: 0.020853 seconds.
- Candidate at 10,000 children: 0.021210 seconds.
- Result: Rejected and reverted. The candidate was 1.7% slower.
- Do not retry without evidence that `ElementTree.tostringlist` emits enough
  fragments for concatenation to dominate serialization.

## Empty-volume Block count without list()

- Date: 2026-10-08
- Package: `nornir-buildmanager`
- Candidate: `sum(1 for _ in volume.findall('Block'))` instead of
  `len(list(...))` on the fail-fast path in `PipelineManager.Execute`.
- Benchmark: pyperf isolated count on in-memory `VolumeNode`, container, idle;
  10 processes, 20 values, 2^18 loops/value; tracemalloc peak on host.
- At 0 Blocks (fail-fast empty volume): list mean 736 ns vs sum 738 ns (not
  significant); tracemalloc peak 707 B vs 926 B (+31% for sum).
- At 203 Blocks: tracemalloc peak 6075 B vs 4531 B (−25% for sum); not the
  empty-volume path this commit targeted.
- Result: Rejected and reverted (`f66e6bb` / umbrella `a4673b8`).
- Do not retry on the empty-volume fail-fast path unless a measured hot path
  materializes large Block lists at pipeline start.

## CreateDistanceImage half-plane broadcast

- Date: 2026-10-08
- Package: `nornir-imageregistration`
- Candidate: Replace the half-plane Python row loop in `CreateDistanceImage`
  with `np.sqrt(y_range[:, np.newaxis] + x_range)` before mirroring.
- Benchmark: pyperf `create_distance_image_shapes` (256², 512², 1024² per
  iteration), container, default processes; old median 4.42 ms, new 4.52 ms;
  `compare_to` not significant (no ≥5% time win). Isolated half-plane at
  512²: row loop ~1.17 ms vs broadcast ~1.59 ms per call.
- Result: Rejected and reverted; no commit.
- Do not retry unless profiling shows the row loop dominates end-to-end assemble
  cache warm-up and a different vectorization avoids extra temporaries.

## Histogram FilenameToTask items() vs list(keys())

- Date: 2026-10-08
- Package: `nornir-imageregistration`
- Candidate: `for f, task in FilenameToTask.items()` instead of
  `list(FilenameToTask.keys())` plus lookup in `Histogram`.
- Benchmark: stub microbench with instant `wait_return`; tracemalloc peak
  32864→112 B and pyperf median 162→123 µs at n=4096; no separate pre/post
  checkout JSON or `pyperf compare_to`; not credible vs real Histogram (I/O
  dominates).
- Result: Rejected and reverted (`5a3df5b` / umbrella `687a5cd`; original
  `6df0708` / `ae7725b`).
- Do not retry unless a real Histogram or end-to-end bench clears cat-18 gates
  with proper compare_to JSON and an old-vs-new equivalence test.
