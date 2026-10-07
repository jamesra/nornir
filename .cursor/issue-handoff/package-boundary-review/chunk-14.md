# Chunk 14 — `refine_shared` and `local_distortion_correction`

## Findings

- Structure is already split into cell roles, validity, measurement, cutoff, discontinuity, progress, and pass diagnostics. `local_distortion_correction.AttemptAlignPoint` is the Pyre entry and should keep calling those helpers rather than growing a second copy.
- No duplicate gate pair stood out as two functions with the same trust question and the same inputs. Retuning thresholds is out of scope.
- `AttemptAlignPoint` is large. A record for one cell’s measurement (offset, weight, peak ratio, role) would shorten its argument lists, but only if it does not change which cells enter the mesh. Not proposed as a behavior change.

## Carry forward

Trust gates untouched.
