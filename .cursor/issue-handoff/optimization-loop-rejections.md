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

## Precompute per-edge constants for _signed_clearance

- Date: 2026-10-19
- Package: `nornir-buildmanager`
- Candidate: In `segmentationtraining/circles.py`, compute `dx`, `dy`,
  `length_sq`, `length_sq > 0` and the safe divisor once in `_edge_arrays`
  instead of on every `_signed_clearance` call from `_refine_center`.
- Benchmark: pyperf, Windows host, idle, `--copy-env`; wobbly star polygon
  in mosaic coordinates (center ~150000, radius ~400 px) at 200 and 60
  vertices; `_refine_center` in isolation and `max_inscribed_circle` end to end.
- Baseline: `_refine_center` 2.60 ms (v200), 2.67 ms (v60);
  `max_inscribed_circle` 230 ms (both).
- Candidate: `_refine_center` 2.08 ms / 2.12 ms (1.25x faster);
  `max_inscribed_circle` 235 / 239 ms, not significant.
- Result: Rejected and reverted. The refinement is about 1% of
  `max_inscribed_circle`; the polygon raster (up to 2048 px side) and
  `distance_transform_edt` take the rest, so the 0.5 ms saving per polygon is
  invisible end to end.
- Do not retry unless the raster/EDT stage is made much cheaper first, so the
  exact refinement becomes a measurable share of the per-polygon cost.

## Vectorize shapes.ring_area_and_centroid shoelace loop

- Date: 2026-10-19
- Package: `nornir-buildmanager`
- Candidate: In `segmentationtraining/shapes.py`, replace the per-vertex
  shoelace loop in `ring_area_and_centroid` with `np.asarray` + `np.roll` and
  sequential `np.cumsum(...)[-1]` sums (bit-identical to the loop; 500-example
  Hypothesis equivalence test passed, incl. -0.0, inf/NaN under `np.errstate`).
- Benchmark: pyperf, Windows host, idle, `-p 10 --copy-env`; closed wobbly
  ellipse rings in mosaic coordinates (~120000, 98000) of 20/100/500/2000
  points, plus `location_shape` end to end on a 500-point POLYGON.
- Baseline: 2.41 us / 10.9 us / 56.5 us / 247 us; `location_shape_500` 2.51 ms.
- Candidate: 17.7 us (7.4x slower) / 27.6 us (2.5x slower) / 70.3 us (1.24x
  slower) / 2000 not significant; `location_shape_500` not significant.
- Result: Rejected and reverted; no commit. Converting the tuple-of-tuples ring
  to an array costs as much as the loop (`np.asarray` ~95 ns/point;
  `np.fromiter(chain.from_iterable(...))` ~35 ns/point by ad hoc timeit) and
  numpy's fixed overhead (~12 us) dominates the small rings. Even the best
  variant saves ~20 us of a 2.5 ms `location_shape` (<1%); parse and
  `simplify_ring` dominate.
- Do not retry unless rings arrive as numpy arrays from parsing (no per-point
  conversion), and an end-to-end `location_shape` / `write_location_shapes`
  bench shows the area/centroid step as a measurable share.

## Exterior-bbox precheck in geometry._maximin_phase_windows

- Date: 2026-10-20
- Package: `nornir-buildmanager`
- Candidate: In `segmentationtraining/geometry.py`, compute each polygon's
  exterior-ring mosaic bbox once per `place_mask_windows` call and skip
  `_window_mask_area` (area 0) for windows that no polygon's bbox can touch,
  so `pixel_rings_in_crop` stops converting every vertex for those windows.
  The precheck can be made exact (not just conservative): `int(round(...))`
  of `(m - origin) / downsample` is monotonic, so the min/max pixel of the
  ring equals the rounded bbox edge and `_ring_touches_image` (itself a bbox
  test) is decided from four numbers.
- Benchmark (count before timing, Windows host, ad hoc script, Pad=1 as in
  `ExportTrainingData`): windows whose exterior ring fails the touch test,
  i.e. the only windows the precheck could skip:
  - one 400-vertex cell, r=6000, ds 1, crop 2048: 0 of 196 area calls;
  - one 600-vertex diagonal strip 40000 px long, ds 1, crop 1024: 0 of 6724
    (2.35 s for the call);
  - same strip, ds 4, crop 512: 0 of 1764 (0.65 s);
  - synthetic MULTIPOLYGON of 3 far-apart 200-vertex parts: 2965 of 3149.
- Result: Rejected; no code change. With the default 1 px pad the padded bbox
  equals the exterior bbox, so for a single polygon every lattice window that
  meets the padded bbox also passes the old (bbox-based) touch test. The skip
  only fires on disjoint multipolygon locations, and no real location data
  with such parts is on this machine, so a benchmark would rest on synthetic
  input the gates forbid.
- Lead (not tried): the strip's cost is real. cProfile of the ds 1 strip:
  `pixel_rings_in_crop` vertex conversion ~1.7 s self + `round` 0.65 s,
  `_clip_ring_to_image` 2.6 s cumulative, over 6724 windows of which 120 are
  kept. Converting per vertex depends only on `origin_x` (x) or `origin_y`
  (y), so the conversions could be hoisted per lattice column/row with the
  same expression (bit-identical); clip and simplify would still run per
  window.
- Do not retry unless real location data shows multipolygon parts far apart
  (or a much larger pad is used), and a pyperf bench on that data shows the
  skip as a significant share of `plan_section_crops`.
