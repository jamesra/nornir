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
