# Nornir master concerns list — bugs and performance

**Started:** 2026-08-26
**Scope:** Nornir umbrella repo (11 submodules), reviewed in 10 chunks.
**Plan:** `nornir_chunked_bug_review_92567ec8.plan.md`

Builds on the Aug 2026 overnight review (`.cursor/overnight-bug-review-progress.md`) and
the CuPy transfer audit (`.cursor/cupy-audit-item-outcomes.md`). Items already fixed
overnight are **not** re-listed; only open/carried items appear below.

## Legend

- **Severity:** P0 (data loss / wrong science), P1 (silent wrong output), P2 (perf / ops pain), P3 (maintainability / debt)
- **Type:** `bug` | `perf` | `parity` | `debt` | `security`
- **Status:** `open` | `confirmed` | `fixed` | `wontfix` | `deferred`

## Chunk status

- [x] 01-foundation (shared + pools)
- [x] 02-phase-stos (phase correlation + STOS brute)
- [x] 03-refine (grid refine + local distortion)
- [x] 04-assemble (assemble + tile I/O)
- [x] 05-transforms (transforms + spatial)
- [x] 06-mosaic (arrange + overlap + layout)
- [x] 07-pipeline (buildmanager pipeline core)
- [x] 08-operations (buildmanager operations)
- [x] 09-importers (importers + dm4)
- [x] 10-pyre (Pyre UI + GL)
- [x] 11-builddashboard (nornir-builddashboard: store, MQTT subscriber, FastAPI app, static UI)
- [ ] 12-infra (Docker, nornir-web, volumecontroller/volumemodel) — optional, still deferred per plan

See the **Summary** at the end of this file for P0/P1 counts, top risks, and recommended fix order.

## Progress

As of 2026-08-31, of the 236 findings tracked in the tables below:

| Status | Count |
|--------|-------|
| `fixed` | 150 |
| `wontfix` | 16 |
| `open` | 69 |
| `confirmed` (reproduced, not yet fixed) | 1 |

One P1 remains: **C00-B001** ([#10](https://github.com/jamesra/nornir-review/issues/10)), the ~3.7 px
golden-gap parity difference against the C++ `ir-refine-grid`, whose test is env-gated. Everything
else still open is P2 or below. The per-row `Status` column is the
authoritative record and carries the fixing commit where one exists — reconciled against the
closed issues on `jamesra/nornir-review`, so a row marked `fixed` has a closed issue whose
closing comment names a commit that resolves in this working tree.

`wontfix` here means **investigated and deliberately not changed** — usually because the
mechanism proved unreachable in current configurations, or because the measured cost of the fix
exceeded the measured benefit. Those issues carry the evidence; several are worth reading before
re-filing the same concern.

Two findings from outside the original review were filed while fixing these and are tracked only
on the issue tracker: [#258](https://github.com/jamesra/nornir-review/issues/258) (fixed —
`SliceToSliceRigidRegistration` raised `TypeError` on every call) and
[#259](https://github.com/jamesra/nornir-review/issues/259) (fixed `b5e6476` — log-polar finalize
skipped/rejected the narrow refine on soft translation peaks; 690→691 error 2.88°→0.77°).

---

## Chunk 00 — Seeded from prior review

Carried forward from overnight Theme 4 (memory-bounded I/O inventory) and the
morning design themes. These are pre-existing, still-open concerns.

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C00-P001 | 00-seed | P0 | perf | `nornir-shared` `FileChecksum` | Reads entire file into memory to hash; large mosaics/STOS on 100TB NAS | Overnight Theme 4 P0 | fixed (`91238b2`) — same defect as C01-P001, which carried the concrete location and the fix; `FileChecksum` now streams via `hashlib.file_digest` | - |
| C00-P002 | 00-seed | P2 | perf | `nornir-shared` / buildmanager `DataChecksum` | Materializes whole mosaic/transform lists; accept for metadata sizes, reject if image bytes embed | Overnight Theme 4 P0 | wontfix (`0a6a32a`) | [#73](https://github.com/jamesra/nornir-review/issues/73) |
| C00-P003 | 00-seed | P1 | perf | `assemble.TransformImage` | Full-section assemble buffers; prefer tileset path + memmap spill | Overnight Theme 4 P1 | fixed (`eaecc9b`) | [#12](https://github.com/jamesra/nornir-review/issues/12) |
| C00-P004 | 00-seed | P1 | perf | `assemble_tiles` output buffer | In-memory output before write; acceptable only with `_use_memmap` | Overnight Theme 4 P1 | wontfix (`8ae12a7`) | [#13](https://github.com/jamesra/nornir-review/issues/13) |
| C00-P005 | 00-seed | P1 | perf | `ConvertImagesInDict*` | Unbounded tile dict; needs in-flight bound + path handoff | Overnight Theme 4 P1 | fixed (`57b2392`) | [#14](https://github.com/jamesra/nornir-review/issues/14) |
| C00-P006 | 00-seed | P2 | perf | `nornir-buildmanager` `mosaicvolume` helpers | Loads full mosaic files into pools; should pass paths and stream tile jobs | Overnight Theme 4 P2 | fixed (`2585c5c`) | [#74](https://github.com/jamesra/nornir-review/issues/74) |
| C00-D001 | 00-seed | P3 | debt | `nornir-imageregistration/transforms` | CPU/GPU dual-class drift invites one-sided fixes (epsilon, Flip, dedupe) | Morning theme 1 | open | [#172](https://github.com/jamesra/nornir-review/issues/172) |
| C00-D002 | 00-seed | P3 | debt | `nornir-buildmanager/volumemanager` | Volume XML dirty/save ownership undocumented; create-on-read getters | Morning theme 2 | open | [#173](https://github.com/jamesra/nornir-review/issues/173) |
| C00-D003 | 00-seed | P1 | bug | `nornir-pools` ParallelPython | ActiveJobCount leak if remote callback never fires; needs bounded wait + unwind | Morning theme 3 | fixed (`5038e62`) | [#11](https://github.com/jamesra/nornir-review/issues/11) |
| C00-D004 | 00-seed | P3 | debt | mosaic / idoc / transform Flip-Flop | No single written axis/origin contract; caused overnight Y-shift bug | Morning theme 5 | open | [#174](https://github.com/jamesra/nornir-review/issues/174) |
| C00-D005 | 00-seed | P3 | debt | `xelementwrapper.py` | Element copy with children marked "possibly undefined behavior", untested | Source comment | open | [#175](https://github.com/jamesra/nornir-review/issues/175) |
| C00-B001 | 00-seed | P1 | parity | grid refine vs C++ `ir-refine-grid` | ~3.7 px golden gap on Grid690 | `test_refine_grid_legacy_parity.py` (env-gated) | open | [#10](https://github.com/jamesra/nornir-review/issues/10) |

---

## Chunk 01 — Foundation: shared + pools

Paths: `nornir-shared/nornir_shared`, `nornir-pools/nornir_pools`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C01-B001 | 01 | P1 | bug | `nornir_shared/histogram.py:195,239,256` | `Median`/`Mean`/`PeakValue` exclude the top bin, so stats use `NumBins-1` bins; feeds auto-level/gamma | `_MinMaxBinIndicies` returns `iMax = NumBins-1`; slices `Bins[iMin:iMax]` | fixed (`ea4e702`) | [#15](https://github.com/jamesra/nornir-review/issues/15) |
| C01-B002 | 01 | P1 | bug | `nornir_shared/histogram.py:29` | `_FindValueAtPercentile` divides by cutoff bin count with no guard; blank tile raises ZeroDivision/IndexError | reached from `Median` and both `AutoLevel` branches | fixed (`88e9f20`) | [#16](https://github.com/jamesra/nornir-review/issues/16) |
| C01-B003 | 01 | P1 | bug | `nornir_shared/files.py:728` | Dir recursion filters on full **path** containing a dot, not dir **name**; a dotted ancestor (e.g. `RC3.v2`) prunes the whole scan | `filter(lambda d: d.path.find('.') > -1, dirs)` — **verified by hand** | fixed (`599bdd2`) | [#17](https://github.com/jamesra/nornir-review/issues/17) |
| C01-B004 | 01 | P1 | bug | `nornir_shared/misc.py:396,400` | Fallback log filename uses `%M` (minutes) where `%m` (month) intended; names mislead and collide across months | `strftime('log-%M.%d.%y_%H.%M.txt')` | fixed (`8995824`) | [#18](https://github.com/jamesra/nornir-review/issues/18) |
| C01-B005 | 01 | P1 | bug | `nornir_pools/parallelpythonpool.py:212,253` | PP pool never implements abstract `num_active_tasks`, so the class cannot be instantiated at all | `IPool.num_active_tasks` is `@abstractmethod`; only `ActiveTasks` defined | fixed (`fba398f`) | [#19](https://github.com/jamesra/nornir-review/issues/19) |
| C01-B006 | 01 | P2 | bug | `nornir_pools/parallelpythonpool.py:218` | `server` property references undefined name `pp`; first submit raises `NameError`, not a missing-cluster error | no `import pp` in module | fixed (`d91c8fb`) | [#75](https://github.com/jamesra/nornir-review/issues/75) |
| C01-B007 | 01 | P2 | bug | `nornir_pools/serialpool.py:24` | `SerialPool._process_pool` reads `self.Name`; `PoolBase` exposes lowercase `name` → `AttributeError` | `GetProcessPool(self.Name + ...)` | fixed (`06ff6da`) | [#76](https://github.com/jamesra/nornir-review/issues/76) |
| C01-B008 | 01 | P2 | bug | `nornir_shared/files.py:677` | Downsample exclusion applies `'%03d' % level` to values `ensure_string_set` may have stringified → `TypeError` | set built at line 673 without int coercion | fixed (`3549e3b`) | [#77](https://github.com/jamesra/nornir-review/issues/77) |
| C01-B009 | 01 | P2 | parity | `nornir_shared/files.py:758-764` vs `793-799` | Threaded recursion branch drops `caseInsensitive` and the `MatchNames is not None` guard; behavior changes past 3 subdirs | serial branch passes both | fixed (`679bfec`) | [#78](https://github.com/jamesra/nornir-review/issues/78) |
| C01-B010 | 01 | P2 | parity | `nornir_pools/multiprocessthreadpool.py:246-273` | `wait_return` returns `None` on failure while `wait` re-raises; callers silently treat failures as empty | `ThreadTask` raises in both | fixed (`23572b3`) | [#79](https://github.com/jamesra/nornir-review/issues/79) |
| C01-B011 | 01 | P2 | bug | `nornir_pools/multiprocessthreadpool.py:351` | Shutdown `assert len(self._active_tasks) == 0` vanishes under `-O`; with asserts on, a leak crashes teardown | callback_wrapper itself raises if id missing | fixed (`e6ba7eb`) | [#80](https://github.com/jamesra/nornir-review/issues/80) |
| C01-B012 | 01 | P2 | debt | `nornir_pools/processpool.py:40,58` | `ImmediateProcessTask.Run` / `_handle_proc_completion` are dead code duplicating process launch; invites re-introducing double-spawn | worker Popens `entry.cmd` itself | fixed (`6e8872f`) | [#81](https://github.com/jamesra/nornir-review/issues/81) |
| C01-B013 | 01 | P2 | bug | `nornir_shared/parallel.py:37,55,115,124` | Lock-file handle leaks on error path; bare `except:` makes stale-lock read indistinguishable from real I/O error | `open()` outside `with`, close skipped on raise | fixed | [#82](https://github.com/jamesra/nornir-review/issues/82) |
| C01-B014 | 01 | P3 | bug | `nornir_pools/task.py:74` | `__str__` pads by length of time string not assembled line; log columns misalign | should measure `out_string` | open | [#176](https://github.com/jamesra/nornir-review/issues/176) |
| C01-B015 | 01 | P3 | bug | `nornir_shared/files.py:593` | `ensure_string_set` returns caller `set`/`frozenset` unchanged, skipping the promised lowercasing | list path lowercases at 599 | open | [#177](https://github.com/jamesra/nornir-review/issues/177) |
| C01-P001 | 01 | P1 | perf | `nornir_shared/checksum.py:64` | `FileChecksum` still `f.read()`s whole file; the open P0 streaming ticket (concrete location for C00-P001) | `return DataChecksum(f.read())` | fixed (`91238b2`) | [#20](https://github.com/jamesra/nornir-review/issues/20) |
| C01-P002 | 01 | P2 | perf | `nornir_shared/files.py:308-397` | `rmtree` submits dir work into the same executor then blocks on `as_completed` inside workers → deadlock/starvation risk on deep trees | nested `rmtree` partial submitted at 350 | fixed | [#83](https://github.com/jamesra/nornir-review/issues/83) |
| C01-P003 | 01 | P2 | perf | `nornir_shared/files.py:737,828` | New 8-worker executor per recursion level and each subtree materialized to a list, defeating the generator API | `ThreadPoolExecutor` per frame; `return list(...)` | fixed | [#84](https://github.com/jamesra/nornir-review/issues/84) |
| C01-P004 | 01 | P2 | perf | `nornir_pools/threadpool.py:239` + `poolbase.py:173` | Queue bounded at `max_threads*32` with blocking `put`; a task enqueueing onto its own pool deadlocks once full | no re-entrancy guard; `tasks.join()` never returns | fixed | [#85](https://github.com/jamesra/nornir-review/issues/85) |
| C01-P005 | 01 | P3 | debt | `nornir_shared/profiling.py:17,128-133` | Phase profiling writes its own NDJSON outside the unified session layout and swallows write errors | `NORNIR_PHASE_PROFILE_LOG`, `except OSError: pass` | open | [#178](https://github.com/jamesra/nornir-review/issues/178) |
| C01-P006 | 01 | P3 | debt | `nornir_shared/misc.py:347-350,383` | With `NORNIR_LOG_ROOT` unset, `SetupLogging` writes logs into CWD, scattering per-run logs | `BaseLoggingDir = os.getcwd()` fallback | open | [#179](https://github.com/jamesra/nornir-review/issues/179) |

**Notes:** Overnight fixes verified as holding (DataChecksum length prefix, shared-memory round trip, PP callback secondary timeout, histogram trim guards, GenNameFromDict). Remaining high-value items are numerical (histogram off-by-one feeds every auto-level decision). PP and Serial pools appear untested — both fail on first use.

---

## Chunk 02 — Phase correlation + STOS brute

Paths: `phasecorrelation.py`, `batched_phase_correlation.py`, `stos_brute.py`, `hann_window_cache.py`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C02-B001 | 02 | P1 | bug | `phasecorrelation.py:577` | `peak_ratio` measured on the **thresholded** surface when `allow_in_place=True`, so 2nd peak is ~0 and the ratio is inflated; gates ambiguity everywhere | line 527 zeroes sub-cutoff in same buffer; `find_offset` (677) and `_peak_from_correlation_image` both pass in-place | fixed (`7a278ed`) | [#21](https://github.com/jamesra/nornir-review/issues/21) |
| C02-B002 | 02 | P1 | bug | `stos_brute.py:676` | `image_stats is None` recovery calls `CalcStats(image_stats)` (passes `None`) instead of `CalcStats(image)`; raises instead of recovering | **verified by hand** | fixed (`65a75f6`) | [#22](https://github.com/jamesra/nornir-review/issues/22) |
| C02-B003 | 02 | P1 | parity | `batched_phase_correlation.py:242` | Batched degeneracy gate weaker than serial `is_alignable_cell`; low-contrast cells serial rejects get noise peaks in batched mode | serial also checks `NORNIR_REFINE_LOW_CONTENT_STD_MIN` | fixed (`db693b2`) | [#23](https://github.com/jamesra/nornir-review/issues/23) |
| C02-B004 | 02 | P1 | bug | `stos_brute.py:1676-1679` | Radial/scale magnitude spectra computed with `use_dog=True`, contradicting documented "DoG for angle, raw for scale" | 4 calls all `use_dog=True`; docstring line 209 | fixed (`1d577b7`) | [#24](https://github.com/jamesra/nornir-review/issues/24) |
| C02-B005 | 02 | P1 | bug | `batched_phase_correlation.py:255-260` | NaN/inf correlation still yields a peak; only weights/ratios zeroed while `peaks` keeps garbage argmax | serial zeroes whole image when `corr_max` non-finite | fixed (`5426429`) | [#25](https://github.com/jamesra/nornir-review/issues/25) |
| C02-B006 | 02 | P1 | bug | `stos_brute.py:1709-1714` | Peak-search normalization divides by `max()` with no zero guard; guarded only by NumPy-only `FloatingPointError` → NaN on CuPy | same at 277-281 | fixed (`1940e60`) | [#26](https://github.com/jamesra/nornir-review/issues/26) |
| C02-B007 | 02 | P2 | bug | `stos_brute.py:1788-1792` | +180° disambiguation rotate omits `power_of_two=True` used by the 0° call; shapes can mismatch the shared target FFT | `fft_phase_correlation` raises on mismatch | wontfix (`cbe6b3c`) | [#86](https://github.com/jamesra/nornir-review/issues/86) |
| C02-B008 | 02 | P2 | bug | `stos_brute.py:286` | Log-polar scale silently clamped to [0.90, 1.12]; a failed estimate is indistinguishable from a good one at the boundary | `np.clip(...)` with no log or flag | fixed (`10abada`) | [#87](https://github.com/jamesra/nornir-review/issues/87) |
| C02-B009 | 02 | P2 | bug | `stos_brute.py:418-435` | `_correlation_peak_ratio` takes global top-2 with no exclusion radius, so "2nd peak" is usually adjacent → ratio collapses to 1.0 | compare `masked_peak_ratio` which uses exclusion radius | open | [#88](https://github.com/jamesra/nornir-review/issues/88) |
| C02-B010 | 02 | P2 | bug | `batched_phase_correlation.py:160-179` | Centroid window clamped rather than truncated, so border peaks refine against an off-center window, biasing offsets inward | `cr = xp.clip(peak_r, r, h-1-r)` | fixed (`977ad81`) | [#89](https://github.com/jamesra/nornir-review/issues/89) |
| C02-B011 | 02 | P2 | bug | `stos_brute.py:855,868` | `NarrowAngleSearchRangeWithResult` uses exact float equality for lookup and can divide by zero `nSteps` | `.index(target_angle)`; `int(range/min_step)` → 0 | fixed (`25ac661`) | [#90](https://github.com/jamesra/nornir-review/issues/90) |
| C02-B012 | 02 | P2 | debt | `phasecorrelation.py:68-76,465,534,545` | Three distinct failure modes all return the same zero-offset record with no logging; `stos_brute` uses `print()` | no `logging` in module; prints at 1267/1436/1712 | fixed (`05036c2`) | [#91](https://github.com/jamesra/nornir-review/issues/91) |
| C02-P001 | 02 | P2 | perf | `batched_phase_correlation.py:73-74,235-236` | Batched force-upcasts every stack to float64, doubling FFT workspace vs serial native dtype | unconditional `dtype=xp.float64` second copy | fixed (`fa84f40`) | [#92](https://github.com/jamesra/nornir-review/issues/92) |
| C02-P002 | 02 | P2 | perf | `stos_brute.py:1678-1679` | DoG+FFT magnitude spectrum computed 4× per log-polar registration when 2 would do | radial pair args identical to angle pair | fixed (`1d577b7`) | [#93](https://github.com/jamesra/nornir-review/issues/93) |
| C02-P003 | 02 | P2 | perf | `stos_brute.py:690` | Per-angle device→host sync in the angle sweep (`int(xp_out.sum(...))`) | called once per angle from `ScoreManyAnglesGpu` | wontfix (`7102c5d`) | [#94](https://github.com/jamesra/nornir-review/issues/94) |
| C02-P004 | 02 | P2 | perf | `stos_brute.py:1311-1314,586-599` | Scale refinement re-zooms source + recomputes full `ImageStats` per score; ternary loop does 14×2 scores → ~40 pad/rotate/FFT cycles | `_SCALE_REFINE_TERNARY_ITERATIONS = 14` | open | [#95](https://github.com/jamesra/nornir-review/issues/95) |
| C02-P005 | 02 | P2 | perf | `hann_window_cache.py` + `stos_brute.py:1772` | Hann window cache is host-only, so the window re-uploads to device every log-polar call | `_coerce_to_source_module` does fresh `xp.asarray` | wontfix (`1f2e6d5`) — unreachable: `xp` is always numpy (host boundary at entry + module-preserving padding), so the coerce returns the identical object |  [#96](https://github.com/jamesra/nornir-review/issues/96) |
| C02-P006 | 02 | P3 | perf | `phasecorrelation.py:464,482` | `count_nonzero(overlap_mask)` evaluated and host-synced twice for the same mask | lines 464 and 482 | open | [#180](https://github.com/jamesra/nornir-review/issues/180) |
| C02-P007 | 02 | P3 | debt | `phasecorrelation.py:563-567` | Sub-pixel offset computed in float32, discarding float64 centroid precision on large frames | float32 cast of `center_of_mass` | open | [#181](https://github.com/jamesra/nornir-review/issues/181) |

**Notes:** Highest-value fix is C02-B001 — every caller passes `allow_in_place=True`, so the uniqueness ratio that gates ambiguity is measured on a surface where sub-cutoff pixels are exactly zero. Serial/batched divergence clusters in the validity gate, the dtype contract, and the non-finite guard, none of which the 4-tile `verify_cpu_vs_batched.py` tolerances would necessarily catch.

---

## Chunk 03 — Grid refine + local distortion

Paths: `local_distortion_correction.py`, `refine_shared/*`, `mosaic_refine.py`, `stos_refine.py`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C03-B001 | 03 | **P0** | parity | `local_distortion_correction.py:4175` | Pooled STOS path builds `EnhancedAlignmentRecord` **without** `peak_ratio`, so every peak-ratio gate silently no-ops: no ambiguous-peak REJECT, empty `soft_discontinuity_ids`, finalize skips the ambiguity bar | 4175-4181 omits the kwarg present at 4100-4108; `is_ambiguous_peak(None)` returns False — **verified by hand** | fixed (`7af0f55`) | [#1](https://github.com/jamesra/nornir-review/issues/1) |
| C03-B002 | 03 | P1 | bug | `local_distortion_correction.py:3762` | `if i == num_iterations - 1: final_pass = True` runs **after** `i += 1`, so refine terminates one pass early | `i += 1` at 3736, break at 3738; comment describes pre-increment | fixed (`bb08aa7`) | [#27](https://github.com/jamesra/nornir-review/issues/27) |
| C03-B003 | 03 | P1 | parity | `local_distortion_correction.py:1408` | Batched returns `None` for a legitimately empty result; caller reads that as "batched unavailable" and re-measures the whole grid through a different peak finder → run-to-run CP differences | `return records if len(records) > 0 else None`; fallback at 4062-4072 | fixed (`d9d81b5`) | [#28](https://github.com/jamesra/nornir-review/issues/28) |
| C03-B004 | 03 | P1 | bug | `local_distortion_correction.py:2772` | Batched ZNCC wrapped in `except Exception: pass` with no logging; fallback sets score 0.0, which is below `identity_zncc_min` → infra failure looks like `IDENTITY_SUSPECT` | 2772-2773, 2798-2799 | fixed (`8d58125`) | [#29](https://github.com/jamesra/nornir-review/issues/29) |
| C03-B005 | 03 | P1 | bug | `refine_shared/phase_timer.py:93` | Two sources of truth for `NORNIR_REFINE_PHASE_TIMING`: module global snapshots env at import, config re-reads per call → benchmarks setting it late get empty buckets | phase_timer 33-37 vs runtime_config 26-29 | fixed (`1603949`) | [#30](https://github.com/jamesra/nornir-review/issues/30) |
| C03-B006 | 03 | P2 | bug | `refine_shared/runtime_config.py:66,81` | Two output-changing flags default ON when unset; `NORNIR_REFINE_SHARP_WARPS` has no recorded golden-gate sign-off | `sharp_flag == '' → True` | open | [#97](https://github.com/jamesra/nornir-review/issues/97) |
| C03-B007 | 03 | P2 | parity | `local_distortion_correction.py:4062` | `NORNIR_REFINE_BATCHED` is documented as the mosaic vertex gate but also gates STOS cell measurement, so `0` moves STOS onto the path that drops `peak_ratio` (C03-B001) | docstring 140-146 scopes it to mosaic | open | [#98](https://github.com/jamesra/nornir-review/issues/98) |
| C03-B008 | 03 | P3 | bug | `local_distortion_correction.py:3139` | Residual/global-FOV recovery branches `continue` without incrementing `i`, so pass `i` runs twice; on the final pass this exceeds the iteration budget | 3112-3139, 3145-3172 | open | [#182](https://github.com/jamesra/nornir-review/issues/182) |
| C03-B009 | 03 | P3 | bug | `local_distortion_correction.py:3837` | `final_grid_n` reads loop-local `alignment_points`; `num_iterations < 1` raises `NameError` instead of a validation error | `RefineTransform` lacks the guard `RefineGridMosaic` has | open | [#183](https://github.com/jamesra/nornir-review/issues/183) |
| C03-B010 | 03 | P3 | debt | `refine_shared/discontinuity.py:21,32` | Duplicate env parse for `NORNIR_REFINE_DISCONTINUITY_K` / `_TRAVEL_MULT` alongside `RefineRuntimeConfig` | two clamp implementations can diverge | open | [#184](https://github.com/jamesra/nornir-review/issues/184) |
| C03-P001 | 03 | P1 | perf | `refine_shared/cell_validity.py:82` | `low_content_std_min_threshold()` calls `get_runtime_config(refresh=True)`, clearing the `lru_cache` and re-reading ~14 env vars **per cell** (×2 per measurement) | all 18 call sites in chunk use `refresh=True` | fixed (`55181da`) | [#31](https://github.com/jamesra/nornir-review/issues/31) |
| C03-P002 | 03 | P1 | perf | `refine_shared/cell_validity.py:76` | Serial path retains 3+ device→host scalar syncs per cell that the batched path removed | `amin == amax`, `amax == 0`, `float(xp.std(...))` | fixed (`8218c0d`) | [#32](https://github.com/jamesra/nornir-review/issues/32) |
| C03-P003 | 03 | P1 | perf | `local_distortion_correction.py:781` | Batched vertex measurement accumulates every candidate cell/mask in lists then stacks twice → peak ≈3× candidate set; downstream FFT chunking cannot bound it | caller stacks before `cell_measurement.py:88-90` budget | fixed | [#33](https://github.com/jamesra/nornir-review/issues/33) |
| C03-P004 | 03 | P1 | perf | `local_distortion_correction.py:1241` | `BuildAlignmentROIsBatched` materializes whole-grid `(N,H,W)` stacks then upcasts both to float64 (~1.6 GB for Grid16-scale, per pass) | 1290-1293 | fixed | [#34](https://github.com/jamesra/nornir-review/issues/34) |
| C03-P005 | 03 | P2 | perf | `local_distortion_correction.py:1028` | Four full-source-image reductions per invocation (isnan/min/max with host syncs) recomputed every pass though the image never changes | `ImageStats` already carries this | wontfix (1089204: measured 1.4% CuPy / 0.7% NumPy of the containing function; NaN answer selects interpolation order and min/max bound the output clip, so a stale cache would change registration output) | [#99](https://github.com/jamesra/nornir-review/issues/99) |
| C03-P006 | 03 | P2 | perf | `refine_shared/anchor_smooth.py:186` | `transform.Transform(point.reshape(1,2))` called once **per record** inside the emit loop; thousands of single-point mesh/RBF queries per pass | batched form exists at 98-104 | open | [#100](https://github.com/jamesra/nornir-review/issues/100) |
| C03-P007 | 03 | P2 | perf | `local_distortion_correction.py:1972` | `_refine_tileset` holds every prewarped tile (image + bool mask) simultaneously; dominant resident set at 100+ tile sections, no chunking or spill | `prewarped` dict, `_PrewarpedTile` | open | [#101](https://github.com/jamesra/nornir-review/issues/101) |
| C03-P008 | 03 | P3 | perf | `local_distortion_correction.py:1979` | `_grid_refine_neighbors` recomputed inside the pass loop, O(N²) in tiles (~16.9k pairs at 130 tiles, every pass) | only bounding boxes change between passes | open | [#185](https://github.com/jamesra/nornir-review/issues/185) |
| C03-P009 | 03 | P3 | perf | `local_distortion_correction.py:2026` | Full `gc.collect()` + CuPy `free_all_blocks()` after every pass forfeits allocator reuse for identically-shaped next-pass stacks | `_release_refinement_worker_memory` | open | [#186](https://github.com/jamesra/nornir-review/issues/186) |

**Notes:** C03-B001 is the single highest-value fix in the whole review so far — a one-kwarg omission that disables the entire peak-ratio reject machinery, failing open rather than erroring. `get_runtime_config(refresh=True)` at all 18 call sites means the `lru_cache` never serves a hit. Batched paths were memory-bounded at the FFT stage only; callers stack the full candidate set upstream of the VRAM budget.

---

## Chunk 04 — Assemble + tile I/O

Paths: `assemble.py`, `assemble_tiles.py`, `tileset.py`, `tileset_functions.py`, `mmap_metadata.py`, `transformed_image_data_temp_files.py`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C04-B001 | 04 | P1 | bug | `assemble.py:809-851` | `TransformStos` returns/saves the **unwarped** source image; the assemble call is commented out and `stos is None` branches are dead | `stos = None` at 820 never reassigned; 844 commented; returns raw `warpedImage` — **verified by hand** | fixed | [#35](https://github.com/jamesra/nornir-review/issues/35) |
| C04-B002 | 04 | P1 | bug | `assemble.py:622-626,688-692` | Both deprecated wrappers discard every caller argument, silently substituting full-bbox warp with cval 0 | pass `None`/`False` literals instead of received args | fixed | [#36](https://github.com/jamesra/nornir-review/issues/36) |
| C04-B003 | 04 | P2 | bug | `assemble.py:456-462` | Empty-subroi shared-memory branch passes the CuPy `output_area` into `create_shared_memory_array` instead of `output_area_shape` | sibling at 557 already corrected | fixed | [#102](https://github.com/jamesra/nornir-review/issues/102) |
| C04-B004 | 04 | P2 | bug | `assemble.py:484-550` | NaN survives the warp: order lowered to 1 but `xp.clip` leaves NaN, and `CompositeImageWithZBuffer` treats NaN as nonzero → written into the canvas | `sub_image != 0` is True for NaN | wontfix | [#103](https://github.com/jamesra/nornir-review/issues/103) |
| C04-B005 | 04 | P2 | bug | `assemble_tiles.py:913-914` | `distance_image_cache` mutated from worker threads without a lock; the lock held at 496 is released before `TransformTile` re-enters the cache | `KeepGetOrCreate` at 914 unlocked | fixed | [#104](https://github.com/jamesra/nornir-review/issues/104) |
| C04-B006 | 04 | P2 | bug | `tileset.py:167-208` | `__CorrectBrightfieldShading` never appends tasks, so the wait loop is dead and it returns before files are written on a non-serial pool | `outputPaths.append` also double-adds | fixed (`fc5eaa7`) | [#105](https://github.com/jamesra/nornir-review/issues/105) |
| C04-B007 | 04 | P2 | bug | `transformed_image_data_temp_files.py:50,177,199` | Class declares `sharedTempRoot` but code reads `_sharedTempRoot`; `SaveArrayToTemporaryFile` raises `AttributeError` unless another call ran first | name mismatch | fixed (`a64408d`) | [#106](https://github.com/jamesra/nornir-review/issues/106) |
| C04-B008 | 04 | P2 | bug | `transformed_image_data_temp_files.py:196-202` | `_temp_folder_created` check-then-set is not thread-safe; concurrent calls each `mkdtemp` and only the last is `atexit`-registered → leaked temp roots | no lock; driven from a threading pool | fixed (`ffb6f71`) | [#107](https://github.com/jamesra/nornir-review/issues/107) |
| C04-B009 | 04 | P2 | bug | `transformed_image_data_temp_files.py:99-101,222-239` | `Clear()` schedules `os.remove` on files whose memmap may still be alive; failures swallowed and never retried → temp file leak | `_RemoveTempFiles` catches `IOError` and logs only | fixed (`baadf45`) | [#108](https://github.com/jamesra/nornir-review/issues/108) |
| C04-B010 | 04 | P2 | bug | `tileset_functions.py:265-269` | Per-tile `os.rmdir(temp_input_dir)` removes the **shared** level cache dir other in-flight tiles are reading | dir is level-wide from caller at 174-176 | wontfix | [#109](https://github.com/jamesra/nornir-review/issues/109) |
| C04-B011 | 04 | P3 | bug | `tileset_functions.py:315-316,362-363` | Silent skips: failed tile open returns `None` via bare `except IOError`; a 3-of-4 quadrant load yields a silently incomplete pyramid tile | warning only fires when all four fail | open | [#187](https://github.com/jamesra/nornir-review/issues/187) |
| C04-P001 | 04 | P1 | perf | `assemble_tiles.py:560-573` | `TilesToImageThreaded` submits all work at once and holds each warped tile until in-order composite → in-flight memory O(tiles), not O(workers) | serial path has `_PREFETCH_DEPTH`, parallel has `CheckTaskInterval`; threaded has no gate | fixed (`b115b52`) | [#37](https://github.com/jamesra/nornir-review/issues/37) |
| C04-P002 | 04 | P1 | perf | `assemble.py:994-1019` | Tiled `TransformImage` sets `return_shared_memory=False`, pickling every 2048² warped tile back through the pool pipe | the matching `unlink_shared_memory` at 1019 silently no-ops on an ndarray | wontfix (`35b85ed`) | [#38](https://github.com/jamesra/nornir-review/issues/38) |
| C04-P003 | 04 | P1 | perf | `assemble.py:964-972,1025-1033` | `enforce_background_cval` re-runs a whole-section inverse transform then copies the whole section after the tiled warp already finished | `GetROICoords` over full canvas + `output.copy()` | fixed (`b9317ac`) | [#39](https://github.com/jamesra/nornir-review/issues/39) |
| C04-P004 | 04 | P2 | perf | `assemble.py:484,538-544` | Three full-array reductions plus host syncs per warp per tile, inconsistent with the kept A1/A7 lazy-stats decisions | `bool(xp.any(xp.isnan(...)))`, min/max, two `float()` | fixed (`fad42c3`) — NaN scan deferred; 10-23% faster CuPy distance-plane warp. Clip cannot be gated on order (border blends toward cval) | [#110](https://github.com/jamesra/nornir-review/issues/110) |
| C04-P005 | 04 | P2 | perf | `assemble.py:583-588` | `return_valid_mask` allocates a full bool mask plus a second full output via `xp.where` instead of in-place cval assignment | peak 2× output + mask | open | [#111](https://github.com/jamesra/nornir-review/issues/111) |
| C04-P006 | 04 | P2 | parity | `assemble_tiles.py:376,540` vs `649` | Output dtype comes from tile 0 in serial/threaded but `default_image_dtype()` in parallel — same mosaic assembles to different dtypes by entry point | also loads a full tile just to read a dtype | open | [#112](https://github.com/jamesra/nornir-review/issues/112) |
| C04-P007 | 04 | P3 | perf | `tileset_functions.py:314` | Each pyramid quadrant decoded then fully re-copied via `tobytes()`, tripling transient memory, four concurrent | `Image.frombytes(..., img.tobytes())` | open | [#189](https://github.com/jamesra/nornir-review/issues/189) |
| C04-D001 | 04 | P3 | debt | `assemble_tiles.py:94-97,173-182,221-231` | The whole spill-to-disk path is disabled behind `_use_memmap() -> False`, and the dead code is internally inconsistent (missing finalizer, possibly-unbound name in `except`) | two standing TODOs; unused `finalizer` | open | [#188](https://github.com/jamesra/nornir-review/issues/188) |

**Notes:** `TransformStos` returning an unwarped image is the sharpest correctness finding here. Memory-boundedness is uneven across the three assemble entry points — only the threaded one has no in-flight gate at all, which is ~3 GB of warped tiles for a 100-tile section at the documented 2-3 GB/core envelope. Path-vs-pickle infrastructure exists but tiled `TransformImage` opts out while retaining the dead unlink call.

---

## Chunk 05 — Transforms + spatial

Paths: `transforms/*`, `spatial/*`, `spatial_distance.py`, `nearest_neighbor.py`

**Regression check on the recent `cdist` fix: intact.** `_cdist_same_dtype` runs first (`spatial_distance.py:89`), `ascontiguousarray` after (94-95), so a dtype-driven copy cannot reintroduce a strided array.

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C05-B001 | 05 | **P0** | bug | `nearest_neighbor.py:72-81` | Same strided-view hazard as the fixed `cdist` bug, still live: `cp.asarray(pts, dtype=float32)` is a **no-op** on an already-float32 CuPy view, and callers pass `_points[:, 2:4]` views (strides 16,4). At >=4096 pts CuVS brute-force reads packed garbage | both `hasattr` branches identical, no `ascontiguousarray` — **verified by hand**; callers `triangulation.py:195,202`, `gridtransform.py:332,339` | fixed (`c323ba1`) | [#2](https://github.com/jamesra/nornir-review/issues/2) |
| C05-B002 | 05 | P1 | parity | `transforms/one_way_rbftransform.py:545-550` | GPU `Transform` does not return early for `UseRigidTransform`; it zeroes weight sums and falls into RBF math with a (1,N)/(N,) broadcast mismatch. CPU twin returns at 197-198 | one-sided twin drift | wontfix (`4b24b9e`) | [#40](https://github.com/jamesra/nornir-review/issues/40) |
| C05-B003 | 05 | P1 | bug | `transforms/utils.py:62` | `InvalidIndices` masks only `isnan`; `±Inf` treated as valid, so an `inf` from the discrete interpolator is never routed to the RBF fallback | every fallback router keys on this mask (`gridwithrbffallback.py:195,231,528,569`) | fixed (`7ae1bc0`) | [#41](https://github.com/jamesra/nornir-review/issues/41) |
| C05-B004 | 05 | P1 | bug | `spatial/converters.py:52-53` | `BoundsArrayFromPoints` uses bare `min`/`max` with no finite guard; one NaN/Inf control point makes the whole bounding box NaN | feeds `Target/MappedBoundingBox`, hence `FlipWarped` default center | fixed (`86d0711`) | [#42](https://github.com/jamesra/nornir-review/issues/42) |
| C05-B005 | 05 | P1 | parity | `transforms/gridwithrbffallback.py:206` | CPU unconditionally downcasts fallback query points to float32; the GPU twin has that line commented out. CPU `InverseTransform` (241) also lacks it, so the CPU class is inconsistent with itself | GPU line 539 is commented | fixed (`aa7551a`) | [#43](https://github.com/jamesra/nornir-review/issues/43) |
| C05-B006 | 05 | P1 | parity | `transforms/controlpointbase.py:322` vs `574` | Host `SourceBoundingBox` uses `BoundingRectangleFromPoints`, GPU `MappedBoundingBox` uses `BoundingPrimitiveFromPoints` — different return types for 3D input; host is also internally inconsistent between its two axes | line 279 uses the primitive variant | fixed (`645071a`) | [#44](https://github.com/jamesra/nornir-review/issues/44) |
| C05-B007 | 05 | P2 | bug | `transforms/controlpointbase.py:463-482` | GPU `GetPointPairsInRect` is a straight copy of the host body: `np.vstack` on CuPy rows and per-point CuPy scalar indexing | no backend adaptation | open | [#113](https://github.com/jamesra/nornir-review/issues/113) |
| C05-B008 | 05 | P2 | bug | `transforms/addition.py:104-105` | `_AddGridTransforms` computes `AToC_pointPairs` and never uses it; the returned grid carries only `TargetPoints`, dropping the composed source correspondence | dead value suggests unwired composition | open | [#114](https://github.com/jamesra/nornir-review/issues/114) |
| C05-B009 | 05 | P2 | bug | `transforms/addition.py:63-79` | Rigid∘rigid adds `target_offset` without rotating by B→C's angle and keeps only A→B's rotation center; correct only when centers coincide and scale is 1 | also reaches into private `_target_offset` | open | [#115](https://github.com/jamesra/nornir-review/issues/115) |
| C05-B010 | 05 | P2 | parity | `transforms/controlpointbase.py:392` | `ControlPointBase_GPUComponent` implements `Flip` but does not inherit `ITransformFlip`, so `isinstance` capability checks silently fail for every GPU control-point transform | host class inherits it at 126 | open | [#116](https://github.com/jamesra/nornir-review/issues/116) |
| C05-B011 | 05 | P2 | bug | `transforms/gridtransform.py:178-179,232-233` | Bare `except Exception: pass` around interpolator evaluation turns OOM/dtype errors into a silent all-NaN return plus a discarded interpolator | non-degenerate `ValueError` branch also lacks `raise` | open | [#117](https://github.com/jamesra/nornir-review/issues/117) |
| C05-B012 | 05 | P3 | parity | `transforms/triangulation.py:575` | Host `Triangulation.Scale` mutates in place while the GPU twin and both Landmark classes rebind; in-place also mutates a caller array passed through without copy | vs 1052, `landmark.py:308,615` | open | [#190](https://github.com/jamesra/nornir-review/issues/190) |
| C05-B013 | 05 | P3 | debt | `nearest_neighbor.py:75-78` | Both branches of the `hasattr(points, 'get')` test execute the identical statement — dead conditional hiding the missing contiguity handling | same line twice | confirmed | [#191](https://github.com/jamesra/nornir-review/issues/191) |
| C05-P001 | 05 | P2 | perf | `nearest_neighbor.py:37-41` | CuVS import gate evaluated once at module import against `UsingCupy()`; a process selecting CuPy later keeps `_cuvs_brute_force is None` and silently never uses the GPU index | `_use_cuvs_nn` short-circuits at 141 | open | [#118](https://github.com/jamesra/nornir-review/issues/118) |
| C05-P002 | 05 | P2 | perf | `transforms/controlpointbase.py:208-215,469-476` | `GetPointPairsInRect` is a per-point Python loop with `np.vstack` per hit — O(N²) copying where a vectorized mask would be one pass | grid transforms route every rect query here | open | [#119](https://github.com/jamesra/nornir-review/issues/119) |
| C05-P003 | 05 | P2 | perf | `transforms/gridwithrbffallback.py:417,759` | `RotateTargetPoints` eagerly rebuilds the whole RBF fallback while `TranslateFixed/Warped` correctly defer via `_defer_continuous_rbf`; interactive rotation pays a full RBF rebuild per event | compare 382-384 / 724-726 | open | [#120](https://github.com/jamesra/nornir-review/issues/120) |
| C05-P004 | 05 | P2 | perf | `transforms/one_way_rbftransform.py:527-528` | Chunked weight-sum loop asserts on a **device** element every iteration, forcing a GPU→host sync per chunk | `assert MatrixWeightSumX[iStart] == 0` inside the while loop | open | [#121](https://github.com/jamesra/nornir-review/issues/121) |
| C05-P005 | 05 | P3 | perf | `transforms/meshwithrbffallback.py:427-436` | GPU rebuild copies both point sets to host, constructs two GPU RBFs from host arrays, and solves serially; the CPU twin fans its two solves to the thread pool | vs CPU 186-198 | open | [#192](https://github.com/jamesra/nornir-review/issues/192) |

**Notes:** C05-B001 is the direct sibling of the bug just fixed in `cdist` and is the top action item; the fix mirrors `spatial_distance.py:94`, and a regression test needs >=4096 points to reach the CuVS branch. Non-finite handling is NaN-only across the whole chunk while `converters.py`/`gridtransform.py` correctly use `isfinite` — the inconsistency matters most at `gridwithrbffallback.py:212/246`. Four twin-drift items (B002, B005, B006, B012) should be added to `docs/cpu_gpu_dual_class_parity.md`.

---

## Chunk 06 — Mosaic arrange + overlap

Paths: `arrange_mosaic.py`, `overlapmasking.py`, `layout.py`, `mosaic_tileset.py`, `mosaic.py`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C06-B001 | 06 | P1 | bug | `layout.py:830-855` | `RelaxNodes` leaves zero rows for isolated nodes, then the movement loop reads every row — node ID 0 gets relaxed once per isolated node (double-moved), or `KeyError` if no node 0 exists | `continue` at 832 skips the assignment at 842; isolated nodes are expected after prune | fixed (`835994c`) | [#45](https://github.com/jamesra/nornir-review/issues/45) |
| C06-B002 | 06 | P1 | bug | `layout.py:1426-1452` | Offset averaging includes rows skipped by `continue`, so the merge offset is biased toward zero | pre-zeroed array + `np.mean(..., axis=0)` at 1452 | fixed (`0ea307b`) | [#46](https://github.com/jamesra/nornir-review/issues/46) |
| C06-B003 | 06 | P1 | bug | `layout.py:1454-1456,1415-1422` | After a merge `layout_list[iLayout_B]` is rebound but pending pair indices are stale, so a later pair can translate a layout against **itself**; `tile_to_layout` is never updated | assert compares indices, not identity | fixed | [#47](https://github.com/jamesra/nornir-review/issues/47) |
| C06-B004 | 06 | P1 | bug | `arrange_mosaic.py:630-638` | `f_score` used outside the `feature_scores is not None` guard that binds it → `UnboundLocalError` when `use_feature_score` is on and scores are None | assigned only at 631-632, used at 636-637 | fixed | [#48](https://github.com/jamesra/nornir-review/issues/48) |
| C06-B005 | 06 | P2 | bug | `arrange_mosaic.py:610-641` | Failed alignments are removed from the layout then immediately re-added with weight 0; the removal is dead and a spurious zero-weight spring survives into relaxation | both except branches set `offset`, falling into `SetOffset` at 641 | fixed (`9c3f79d`) | [#122](https://github.com/jamesra/nornir-review/issues/122) |
| C06-B006 | 06 | P2 | bug | `arrange_mosaic.py:455-462` | Feature-score normalization divides by a max that can be 0 (all-blank tiles); `max()` also raises `TypeError` on the `None` scores `ScoreTileOverlaps` explicitly allows | `max_score = 0` only grows via `max(...)` | fixed (`6fd2a66`) | [#123](https://github.com/jamesra/nornir-review/issues/123) |
| C06-B007 | 06 | P2 | bug | `layout.py:347-362,1000-1006` | `ScaleOffsetWeightsByPosition` is unconditionally broken — a `raise NotImplementedError` sits after the computation, before the assignment; the public wrapper calls it for every node | unreachable line 360 | wontfix (`7cbac3e`) | [#124](https://github.com/jamesra/nornir-review/issues/124) |
| C06-B008 | 06 | P2 | bug | `layout.py:321-332` | `MaxTensionMagnitude` sums over axis 1 of a 1-D `(2,)` vector → `AxisError`; the subsequent `argmax` on a scalar is meaningless | `np.sum(v ** 2, 1)` at 330 | fixed (`e4a047e`); the sibling ID-index defect found alongside it is #255, fixed in `b65c89f` | [#125](https://github.com/jamesra/nornir-review/issues/125) |
| C06-B009 | 06 | P2 | parity | `overlapmasking.py:265` vs `294,326` | The brute-force **reference** mask reduces over the wrong axis (per-image min vs per-dimension min), so any parity check against it is invalid | axis 1 vs axis 0 | fixed (`c74916d`) | [#126](https://github.com/jamesra/nornir-review/issues/126) |
| C06-B010 | 06 | P2 | bug | `arrange_mosaic.py:661-665` | Default `cval='random'` reaches `np.isnan(cval)` → `TypeError` on the documented default `dtype=None` path | `issubdtype` False so `isnan('random')` evaluates | fixed (`140045e`) | [#127](https://github.com/jamesra/nornir-review/issues/127) |
| C06-B011 | 06 | P2 | bug | `arrange_mosaic.py:120-247` | `relaxed_layout` can still be `None` at loop exit (break on pass 0 with no qualifying overlaps) and is then dereferenced | `# type: ignore[union-attr]` acknowledges the unproven invariant | fixed (`62edf23`) | [#128](https://github.com/jamesra/nornir-review/issues/128) |
| C06-B012 | 06 | P2 | bug | `layout.py:217-230` | `RemoveOffset`'s warning is a no-op — it constructs a `Warning` object and discards it — and sits outside the `if`, so it also "fires" on success | should go through logging per the unified rule | fixed (`76389b0`) | [#129](https://github.com/jamesra/nornir-review/issues/129) |
| C06-B013 | 06 | P2 | parity | `layout.py:1009-1053` vs `1065-1113` | `NormalizeOffsetWeights` and `ScaleOffsetWeightsByPopulationRank` interpret `min/max_allowed_weight` in opposite directions, so the configured weight floor is never applied by `TranslateTiles2` | docstring contradicts the mapping at 1046 | fixed (`d4ca8f8`) | [#130](https://github.com/jamesra/nornir-review/issues/130) |
| C06-B014 | 06 | P3 | bug | `mosaic.py:158-171` | `mapped_bbox_shape` unbound when `all_same_dims=False` → `UnboundLocalError` on the documented non-default path | assigned only inside the `if` | open | [#193](https://github.com/jamesra/nornir-review/issues/193) |
| C06-B015 | 06 | P3 | bug | `arrange_mosaic.py:983-988` | `finally` block `del`s names that may be unbound, raising `NameError` and masking the original exception | `del OverlappingRegionA/B` | open | [#194](https://github.com/jamesra/nornir-review/issues/194) |
| C06-B016 | 06 | P3 | bug | `arrange_mosaic.py:735` | `__tile_offset_remote` hard-overwrites its `excess_scalar` parameter with literal `2`, so `TranslateSettings.excess_scalar` has no effect; the adjacent comment says 1 | parameter shadowed immediately | open | [#195](https://github.com/jamesra/nornir-review/issues/195) |
| C06-P001 | 06 | P2 | perf | `layout.py:830-855,1161-1177` | Relaxation computes `WeightedNetTensionVector` twice per node per iteration, then `MaxWeightedNetTensionMagnitude` recomputes them all again — ~3× work in a function whose own comment calls it a bottleneck | line 850 comment | fixed (`fc1acc3`) | [#131](https://github.com/jamesra/nornir-review/issues/131) |
| C06-P002 | 06 | P2 | perf | `layout.py:128-136,295-345` | `OffsetArray` property allocates a full copy plus `setflags` on **every** access, and tension helpers index it once per node per query | should use `_OffsetArray` internally | fixed (`61f23fd`) | [#132](https://github.com/jamesra/nornir-review/issues/132) |
| C06-P003 | 06 | P2 | perf | `layout.py:983-995,199-210` | Quadratic array growth: `OffsetsSortedByWeight` `vstack`s per node and `SetOffset` re-sorts the full offset array on every insertion | collect into a list and concatenate once | fixed (`c58b1db`) | [#133](https://github.com/jamesra/nornir-review/issues/133) |
| C06-P004 | 06 | P3 | perf | `overlapmasking.py:54-71` | LRU insert recomputes total cache bytes by summing every entry — O(entries) per insertion against a 512 MB budget of small masks | running counter would be O(1) | open | [#196](https://github.com/jamesra/nornir-review/issues/196) |
| C06-P005 | 06 | P3 | perf | `layout.py:1297-1324` | `MergeDisconnectedLayouts` grows `matrix_A` and runs a full pairwise `cdist` against every previously merged node — O(N²) work and memory across a section | line 1311/1324 | open | [#197](https://github.com/jamesra/nornir-review/issues/197) |

**Notes:** No `set.add(iterable)` misuse found; `nonoverlapping_tile_IDs -= set(overlap.ID)` is correct but fragile, and `removed_offset_IDs` is annotated `set[int]` while holding tuples. Per A5 nothing here proposes parallelizing `find_offset` — but note `_FindTileOffsets` (567-570) only forces the serial pool under CuPy, so the "arrange stays serial" guidance and the NumPy code path diverge and deserve an explicit decision. Exact float position comparisons in `mosaic_tileset.py:222,227` pass today only because the translation is exact subtraction.

---

## Chunk 07 — Buildmanager pipeline core

Paths: `pipelinemanager.py`, `build.py`, `volumemanager/*`, `validation/*`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C07-B001 | 07 | **P0** | bug | `volumemanager/pyramidlevelhandler.py:70-77` | `GetScale()` never advances the walk variable — guaranteed infinite loop / build hang whenever no ancestor exposes `Scale` | line 75 is `Parent = self.Parent` again instead of `Parent.Parent` — **verified by hand** | fixed (`395ade3`) | [#3](https://github.com/jamesra/nornir-review/issues/3) |
| C07-B002 | 07 | **P0** | bug | `volumemanager/channelnode.py:78-84` | `ChannelNode.Scale` always returns `None`; `__init__` sets `self._scale = None`, so the `hasattr(self, '_scale') is False` guard never fires and the lazy XML read is dead code | any channel loaded from XML reports no scale until `SetScale` runs in-process — **verified by hand** | fixed | [#4](https://github.com/jamesra/nornir-review/issues/4) |
| C07-B003 | 07 | **P0** | bug | `volumemanager/mosaicbasenode.py:48-57` | `Checksum` getter writes `attrib['Checksum']` **without** setting `_AttributesChanged`, so the computed checksum is silently discarded; also stores `None` when the file is missing, which will later fail string validation | contrast `ResetChecksum` (46) and the setter (63), which both set the flag | fixed | [#5](https://github.com/jamesra/nornir-review/issues/5) |
| C07-B004 | 07 | P1 | bug | `volumemanager/xcontainerelementwrapper.py:281-287` | `_replace_links` validates/cleans the wrong element — `wrapped_loaded_element` is whatever the previous loop left bound, never rebound in the `clean_tasks` loop | assigned at 243 in the first loop | fixed | [#49](https://github.com/jamesra/nornir-review/issues/49) |
| C07-B005 | 07 | P1 | bug | `volumemanager/xcontainerelementwrapper.py:282-287` | `if IsValid:` tests a `(bool, reason)` tuple, always truthy, so invalid linked containers are never cleaned on the multi-link path | `IsValid()` returns a tuple (`xelementwrapper.py:333`); the `else` at 287 is unreachable | fixed | [#50](https://github.com/jamesra/nornir-review/issues/50) |
| C07-B006 | 07 | P1 | bug | `volumemanager/xelementwrapper.py:874-880` | A read-only query writes the volume to disk: `findall` calls `self.Save()` while resolving links, so any `Filters`/`Sections`/`Levels` access can rewrite VolumeData.xml. Sibling `find` (833) deliberately does not | the two accessors disagree | fixed (`f729884`) | [#51](https://github.com/jamesra/nornir-review/issues/51) |
| C07-B007 | 07 | P1 | bug | `volumemanager/filternode.py:70-79,101-111` | Create-on-read: `TilePyramid` and `Imageset` **properties** append a new child, marking the filter dirty during a query | `append` sets `_ChildrenChanged`; `HasTilePyramid`/`HasImageset` sit beside them doing the non-mutating check | fixed (`1d39d8e`) | [#52](https://github.com/jamesra/nornir-review/issues/52) |
| C07-B008 | 07 | P1 | bug | `volumemanager/blocknode.py:121-143` | `NonStosSectionNumbers` getter rewrites `StosExemptNode.text` and forces `_AttributesChanged` during a read | docstring only promises it won't create the child | fixed (`f20850d`) | [#53](https://github.com/jamesra/nornir-review/issues/53) |
| C07-B009 | 07 | P1 | bug | `volumemanager/xelementwrapper.py:779-788` | `_ReplaceChildElementInPlace` swaps via `self[i] = new`, bypassing `append`/`remove`, so `_ChildrenChanged` is never set — `ReplaceChildWithLink` converts a container to a link stub without marking the parent dirty | vs `append` (731) / `remove` (738) | fixed (`f46af12`) | [#54](https://github.com/jamesra/nornir-review/issues/54) |
| C07-B010 | 07 | P1 | bug | `volumemanager/inputtransformhandler.py:201-204` | Recursive `EnumerateTransformDependents` drops `child_element_name`, so recursion searches with `findall(None)` | 4 args against a 5-param signature | fixed (`6a873ea`) | [#55](https://github.com/jamesra/nornir-review/issues/55) |
| C07-B011 | 07 | P1 | bug | `volumemanager/channelnode.py:89-92` | `_try_remove_scale_node` deletes the `Scale` child but leaves `_scale` populated, so a stale Scale stays readable through the property | only `SetScale` repopulates | fixed (`85977d0`) | [#56](https://github.com/jamesra/nornir-review/issues/56) |
| C07-B012 | 07 | P2 | bug | `volumemanager/xelementwrapper.py:651-659` | `Contains` unpacks `for k, v in c.attrib` — iterating a dict yields keys, so this raises for any attribute name whose length is not 2; it also ignores its `Element` parameter entirely | line 653 | open | [#134](https://github.com/jamesra/nornir-review/issues/134) |
| C07-B013 | 07 | P2 | bug | `pipelinemanager.py:1030-1036` | Stage functions are documented as allowed to return `True`/`False`, but `_SaveNodes` passes the bool to `VolumeManager.Save`, which raises `ValueError` | no bool guard at 930-948 | open | [#135](https://github.com/jamesra/nornir-review/issues/135) |
| C07-B014 | 07 | P2 | bug | `validation/transforms.py:19,55` | Bare `except:` around `float(...)` swallows `KeyboardInterrupt`/`SystemExit`; the comment shows `except ValueError` was intended | two sites | open | [#136](https://github.com/jamesra/nornir-review/issues/136) |
| C07-B015 | 07 | P2 | bug | `volumemanager/xcontainerelementwrapper.py:255-258` | Broad `except Exception: continue` in parallel link loading leaves the unresolved `*_Link` stub in the tree; the single-link path re-raises instead | divergent handling at 197-200 | open | [#137](https://github.com/jamesra/nornir-review/issues/137) |
| C07-B016 | 07 | P2 | bug | `volumemanager/xcontainerelementwrapper.py:224-233` | Loop variable `fullpath` shadows the function parameter, so every error message in the except blocks reports an arbitrary child path | messages at 248, 252, 257 | open | [#138](https://github.com/jamesra/nornir-review/issues/138) |
| C07-B017 | 07 | P2 | bug | `pipelinemanager.py:640-642` | `_WriteStageTimings` reads `StageTimings.json` with an unguarded `json.load`; a truncated file from a killed run raises inside `Execute`'s `finally`, masking the original exception | call site is `finally:` at 614 | open | [#139](https://github.com/jamesra/nornir-review/issues/139) |
| C07-B018 | 07 | P3 | debt | `volumemanager/volumemanager.py:85-90` | `__SortNodes__` reaches into `element._children`, which does not exist on the C-accelerated `ElementTree.Element` | line 87 | open | [#198](https://github.com/jamesra/nornir-review/issues/198) |
| C07-P001 | 07 | P1 | perf | `volumemanager/xelementwrapper.py:883-918` | `findall` runs the same XPath scan **three** times per call and the middle loop discards its result; combined with C07-B006, every property-style enumeration is a triple scan plus a possible disk write | 883, 890-902, 904 | fixed (`3376d19`) | [#57](https://github.com/jamesra/nornir-review/issues/57) |
| C07-P002 | 07 | P2 | perf | `pipelinemanager.py:866-868` | `ProcessIterateNode` materializes every iterate candidate into a list before processing any, defeating the streaming contract; each resolution may force linked VolumeData.xml loads | only `len()` needs the list | open | [#140](https://github.com/jamesra/nornir-review/issues/140) |
| C07-P003 | 07 | P2 | perf | `volumemanager/xcontainerelementwrapper.py:485-486` | One dirty attribute rewrites the container's entire VolumeData.xml with full backup rotation and subtree re-indent; no per-node or append-only path | `__SaveXML` 503-595 | open | [#141](https://github.com/jamesra/nornir-review/issues/141) |

**Notes on the dirty/save model as found:** ownership is per-`XContainerElementWrapper` with `SaveAsLinkedElement == True` — each owns one `VolumeData.xml` and its own `_AttributesChanged`/`_ChildrenChanged` pair, set at mutation time by `append`/`remove`/`__setattr__`/`__delattr__` and cleared by `ResetElementChangeFlags` after a successful write. Linked-child dirtiness deliberately does not bubble; non-linked children are consulted via `ElementHasChangesToSave`. The model is now documented in docstrings (morning theme 2 partly addressed) but **not enforced**: three escape hatches break it — direct `attrib[...]` writes that skip the flag (C07-B003), in-place child replacement (C07-B009), and reads that dirty or save (C07-B006/B007/B008).

**The `if element:` truthiness bug class is essentially absent** from this tree — every element test uses `is None` / `is not None`. The analogous mistake that *is* present is testing a `(bool, reason)` tuple for truth (C07-B005), which fails in the same silent direction. Save-on-read is the dominant remaining structural problem, and two of the three P0s are single-line logic slips that fail as "no scale" or "slow" rather than as an exception, which is why tests miss them.

---

## Chunk 08 — Buildmanager operations

Paths: `operations/block.py`, `operations/tile.py`, `operations/stosgroup_workers.py`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C08-B001 | 08 | **P0** | bug | `operations/block.py:3414-3422` | NaN/Inf compose failure is escalated to a hard `NornirUserException` that aborts the whole SliceToVolume stage; non-NaN errors fall through to the graceful log/`Clean()`/`continue` immediately below, so the NaN case is *deliberately* the only hard failure. Contradicts the design intent that unmapped points be filled by the RBF fallback | `_reraise_stos_nonfinite(...)` precedes the skip path — **verified by hand** | wontfix | [#6](https://github.com/jamesra/nornir-review/issues/6) |
| C08-B002 | 08 | **P0** | bug | `nornir-imageregistration/.../files/stosfile.py:1168-1170` | The composition raises `ValueError("...introduced NaN/Inf transform values")` on its own **output** text, so one unmapped grid point kills the hop that C08-B001 then turns into a run abort | `if transform_text_contains_nonfinite(A_To_C_Stos.Transform): raise` | wontfix | [#7](https://github.com/jamesra/nornir-review/issues/7) |
| C08-B003 | 08 | P1 | bug | `operations/block.py:2908-2912` | `_reraise_stos_nonfinite` classifies by substring `'nan' in text or 'inf' in text`, so any unrelated error whose message contains "info", "insufficient", or a path with `inf` is misreported as a NaN transform and hard-aborted | `text = str(err).lower()` | fixed (`d20c3bb`) | [#58](https://github.com/jamesra/nornir-review/issues/58) |
| C08-B004 | 08 | P1 | bug | `operations/block.py:4147-4179` | `MosaicToVolume`: per-tile `AddTransforms` failures are swallowed by a bare `except:` that only warns; the failed tile keeps its **original section-space** transform and the mosaic is saved as valid with a fresh checksum → silently mis-registered output that will never be rebuilt | `except:` then `Save(...)` + `ResetChecksum()` | fixed (`55f0a56`) | [#59](https://github.com/jamesra/nornir-review/issues/59) |
| C08-B005 | 08 | P1 | bug | `operations/block.py:2477-2481` | Because refine is serial (C08-P002), `_run_refine_or_manual_copy` re-raising every `RefineFunc` exception aborts the entire refine stage on the first bad slice; sibling slices never run | `except Exception as e: ...; raise` | fixed (`e5457c2`) | [#60](https://github.com/jamesra/nornir-review/issues/60) |
| C08-B006 | 08 | P2 | bug | `operations/block.py:3883-3890` | `ScaleStosGroup` raises past `ReleaseStagePools()` with no `try/finally`, leaking the stage pool into the next stage. Same shape at `block.py:4043`, `block.py:1374`, `tile.py:2204`; only `tile.py:3177-3181` uses `finally` | release sits on the happy path | open | [#142](https://github.com/jamesra/nornir-review/issues/142) |
| C08-B007 | 08 | P2 | bug | `operations/block.py:4131-4134` | Third independent NaN hard-abort site, on the SliceToVolume STOS entering `MosaicToVolume`; one bad slice aborts the whole block's stage | `raise _stos_nonfinite_user_error` | open | [#143](https://github.com/jamesra/nornir-review/issues/143) |
| C08-B008 | 08 | P2 | bug | `operations/block.py:3956-3960` | `LinearBlendStosGroup` omits `chain_consistent_linear=` from `IsLinearBlendParamsMatched`, so toggling `-ChainConsistentLinear` does not invalidate its outputs → stale blends silently reused | SliceToVolume path passes it at 3354-3359 | open | [#144](https://github.com/jamesra/nornir-review/issues/144) |
| C08-B009 | 08 | P2 | bug | `operations/tile.py:921-926` | `NumberOfTiles += 1` accumulates across re-runs (get-or-create level, never reset); the inflated count breaks the up-to-date shortcut at `tile.py:2670`, forcing full pyramid rebuilds forever | `if exists: NumberOfTiles += 1` | open | [#145](https://github.com/jamesra/nornir-review/issues/145) |
| C08-B010 | 08 | P2 | bug | `operations/block.py:1756-1767` | `except: pass` in "best mean" selection swallows every per-mapping failure, so a section can end with `WinningTransform is None` and be silently dropped from the output stos map | bare except in the `wait_return` loop | open | [#146](https://github.com/jamesra/nornir-review/issues/146) |
| C08-B011 | 08 | P3 | bug | `operations/block.py:243-273,282-298` | `except: pass` hides malformed ir-stom output; the adjacent `while True` filename-randomization loop has no max attempts and no backoff | 272, 282 | open | [#199](https://github.com/jamesra/nornir-review/issues/199) |
| C08-B012 | 08 | P3 | bug | `operations/block.py:2866-2870` | `except Exception: old_full = None` silently skips migration of an existing short-named STOS file, orphaning it and its `.unblended` sidecar | try/except around `FullPath` | open | [#200](https://github.com/jamesra/nornir-review/issues/200) |
| C08-B013 | 08 | P3 | bug | `operations/block.py:2062` | `OutputDownsample == InputDownsample` compares an XML-sourced `float` (default `'NaN'`, `stosgroupnode.py:33`) against an `int` pipeline arg; a `NaN` default makes it always false, silently forcing a rescale | mixed types | open | [#201](https://github.com/jamesra/nornir-review/issues/201) |
| C08-P001 | 08 | P1 | perf | `operations/block.py:4154-4163` | Unbounded `pool.add_task` over every tile of a section with no in-flight gate; each task pickles a whole dense-grid `StoVTransform`, and all composed results are retained | violates streaming rule at the 2-3 GB/core envelope | fixed (`164f824`) | [#61](https://github.com/jamesra/nornir-review/issues/61) |
| C08-P002 | 08 | P1 | perf | `operations/block.py:2619-2620` | STOS grid refine — the most expensive STOS stage — is dispatched `pool=None, max_in_flight=1`, i.e. fully serial regardless of `workers`, while `ScaleStosGroup`/`LinearBlendStosGroup` do use a pool. Looks like a leftover debug pin | `run_bounded_stos_jobs(None, pool_jobs, max_in_flight=1)` | wontfix (`dc22a6b`) | [#62](https://github.com/jamesra/nornir-review/issues/62) |
| C08-P003 | 08 | P2 | perf | `operations/tile.py:3127-3136` | The documented "map one column, wait for the previous" gate is broken: `last_column_tasks` is dead and `extend(executor.map(...))` eagerly drains each row, so rows never overlap **and** every row's results accumulate for the whole level | assigned-never-used variable | open | [#147](https://github.com/jamesra/nornir-review/issues/147) |
| C08-P004 | 08 | P2 | perf | `operations/tile.py:2989-3010` | ImageMagick tileset row gate awaits only the **first** task of a row, and only past a 256/512 queue-depth threshold — a wide section can enqueue thousands of `magick montage` subprocesses first | `FirstTaskForRow.wait()` behind qsize | fixed (`ebc79f0`) | [#148](https://github.com/jamesra/nornir-review/issues/148) |
| C08-P005 | 08 | P2 | perf | `operations/tile.py:897-919,475-498` | Invert and min-correction stages glob every tile of a level and queue one task per tile with no in-flight gate, then drain | unbounded queue depth on NAS-sized levels | fixed (`82a73a7`) | [#149](https://github.com/jamesra/nornir-review/issues/149) |
| C08-P006 | 08 | P3 | perf | `operations/tile.py:2662-2685` | Pyramid level check builds full glob lists plus three frozensets of basenames for both levels on every transition — O(tiles) host memory per level | streaming `scandir` compare would do | open | [#203](https://github.com/jamesra/nornir-review/issues/203) |
| C08-D001 | 08 | P3 | debt | `tile.py:345,752,2057`; `block.py:3718,3766`; `registration.py:141` | Open TODOs on correctness-relevant paths: 8-bit-only background assumption, unverified gamma match, non-robust tileset-populated check, transforms referencing deleted filters | TODO grep | open | [#202](https://github.com/jamesra/nornir-review/issues/202) |

**Notes — answers to the three targeted checks:**

1. **Unmapped/NaN points are still a hard failure, in three places.** `stosfile.py:1168` raises on the composed *output* text; `block.py:3414` converts that into a stage-aborting `NornirUserException` (while the non-NaN branch right below correctly logs, cleans, and continues); `block.py:4131` raises again in `MosaicToVolume`. Input-side guards are defensible validation, but the output-side raise directly contradicts the intent that unmapped points be RBF-filled and squared up by linearize.
2. **Non-finite checks are consistent** — everything funnels through `transform_text_contains_nonfinite`, covering both NaN and Inf. The weakness is the *classifier* (C08-B003), not the checker.
3. **Row/column gating is partial.** STOS group stages are properly gated via `run_bounded_stos_jobs(max_in_flight=...)`, but `block.py:4154`, `tile.py:897`, and `tile.py:481` queue one task per tile for a whole section with no gate; `tile.py:2989` gates only on a row's first task behind a queue-depth threshold; `tile.py:3127` has lost its column gate to dead code. Only the level-001 save path (`tile.py:1796`, bounded `queue.Queue`) is correctly bounded.

---

## Chunk 09 — Importers + DM4

Paths: `nornir_buildmanager/importers/*`, `dm4/`

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C09-B001 | 09 | **P0** | bug | `importers/mrc.py:340` vs `385-405` | Tile image is Y-flipped but the mosaic coordinates never are, and `FlipList` is declared but never read → systematic Y-shift/mirror for every MRC section | `np.flipud(img)` in `ExportImage`; `CreateMosaic` builds `warped_offset=pixel_position` with no Y inversion; `FlipList` appears only in signatures at 50, 74, 93 — **verified by hand** | fixed (`4d1d1d1`) | [#8](https://github.com/jamesra/nornir-review/issues/8) |
| C09-B002 | 09 | P1 | bug | `importers/mrc.py:332-341` | Flip is applied only on the contrast-adjusted branch, so tile orientation depends on whether `min_max_gamma` was supplied | the `if min_max_gamma is None` branch has no flip — **verified by hand** | fixed (`4d1d1d1`) | [#63](https://github.com/jamesra/nornir-review/issues/63) |
| C09-B003 | 09 | P1 | bug | `importers/mdoc.py:120-122` | `ContrastCutoffs` passed positionally as `(0.0, 100.0)` into an importer whose contract is 0-1 fractions, so `AutoLevel(0.0, 1.0-100.0)` gets a large negative tail | `idoc.py:144-151` rejects cutoffs outside 0-1; `shared.py:650` computes `1.0 - cutoffs[1]` | fixed (`77bc120`) | [#64](https://github.com/jamesra/nornir-review/issues/64) |
| C09-B004 | 09 | P1 | bug | `importers/dm4.py:288-379` | `FlipList` and `ContrastMap` are accepted and forwarded by `Import` but never read in `ToMosaic` — DM4 sections listed in FlipList.txt import unflipped and contrast overrides are silently dropped | neither name appears again in the body | fixed (`62fdc8b`) | [#65](https://github.com/jamesra/nornir-review/issues/65) |
| C09-B005 | 09 | P1 | bug | `importers/dm4.py:444-445` | Grid bounds assert compares the **X** index against the **Y** grid extent, so out-of-grid tiles pass and in-grid tiles can falsely assert | `grid_position[1]` is the X index but is compared to `YDim` | fixed (`7bce4b4`) | [#66](https://github.com/jamesra/nornir-review/issues/66) |
| C09-B006 | 09 | P1 | bug | `importers/pmg.py:240-243` | Flip applied to mosaic coordinates but explicitly disabled for the images — the exact inverse of the MRC bug | `ConvertImagesInDict(..., Flip=False)` then `MosaicFile.Write(..., Flip=Flip)` | wontfix (`4d1d1d1`) | [#67](https://github.com/jamesra/nornir-review/issues/67) |
| C09-B007 | 09 | P1 | bug | `importers/pmg.py:50-51` | PMG importer defaults its search extension to `idoc`, so a plain PMG import matches nothing and silently returns having imported zero sections | `if extension is None: extension = 'idoc'` | fixed (`f991c4c`) | [#68](https://github.com/jamesra/nornir-review/issues/68) |
| C09-B008 | 09 | P1 | bug | `importers/dm4.py:29,189-195` | `TileExtension = 'png'` contradicts its own comment; 16-bit data is loaded as `I;16`, converted to mode `I`, and saved as PNG, which Pillow cannot write for 32-bit integer images | comment says "we use the npy extension" | fixed (`65372d8`) | [#69](https://github.com/jamesra/nornir-review/issues/69) |
| C09-B009 | 09 | P2 | bug | `importers/idoc.py:938-942` | Camera clamp uses `1 << bpp` instead of `(1 << bpp) - 1`, one greater than the real max; the histogram path in the same file uses the correct form | vs `idoc.py:609` | fixed | [#150](https://github.com/jamesra/nornir-review/issues/150) |
| C09-B010 | 09 | P2 | bug | `importers/idoc.py:952-966` | `GetImageBpp` fallback is dead — `DataMode` is always set in `__init__`, so an idoc without a DataMode line returns `None` instead of deriving bpp from Max | `self.DataMode = None` at 916 | fixed | [#151](https://github.com/jamesra/nornir-review/issues/151) |
| C09-B011 | 09 | P2 | bug | `importers/idoc.py:1058-1059` | Unvalidated metadata parsing: `values[0]` / `vTemp[0]` raise `IndexError` on a key with an empty value, aborting the whole idoc load | no length guard before `vTemp[0].isdigit()` | fixed | [#152](https://github.com/jamesra/nornir-review/issues/152) |
| C09-B012 | 09 | P2 | bug | `importers/idoc.py:355-361,428-438` | Missing-tile removal followed by renumber-from-zero silently shifts tile identity, so target tile N no longer corresponds to source tile N; an extension case mismatch on a case-sensitive filesystem drops all tiles | the log at 357 already suspects extension mismatch; `ImageNumber += 1` at 738 | fixed | [#153](https://github.com/jamesra/nornir-review/issues/153) |
| C09-B013 | 09 | P2 | bug | `importers/dm4.py:250-259` | Bare `except:` around both `int()` conversions; an unexpected filename layout yields `section_number = None`, which flows into `GetOrCreateSection(None)` | no format validation | fixed (`cdf6238`) | [#154](https://github.com/jamesra/nornir-review/issues/154) |
| C09-B014 | 09 | P2 | bug | `importers/dm4.py:343-352` | Scale unit conversion handles only `µm`/`um` with no else/raise; Angstrom, `m`, or `mm` silently produce a scale off by orders of magnitude | `nm` works only by accident | fixed | [#155](https://github.com/jamesra/nornir-review/issues/155) |
| C09-P001 | 09 | P1 | perf | `importers/idoc.py:183-191` | The section generator is fully materialized before any import work starts, delaying the first section by a NAS-wide scan and defeating the incremental design its own comment documents at 201-202 | `found_sections = list(find_sections(...))` | fixed (`6b0288c`) | [#70](https://github.com/jamesra/nornir-review/issues/70) |
| C09-P002 | 09 | P1 | perf | `importers/mrc.py:276-285,310-319` | Unbounded task queueing: one memmap plus one histogram task per tile for the whole file, and `ExportImages` queues every tile before waiting — in-flight memory scales with tile count, not cores | single `pool.shutdown()` after the full loop | fixed (`34cbe5a`) | [#71](https://github.com/jamesra/nornir-review/issues/71) |
| C09-P003 | 09 | P2 | perf | `dm4/dm4/dm4file.py:320-345` + `importers/dm4.py:182-195` | Whole-image DM4 reads with no offset/count or memmap, then a second full copy via `.tobytes()` → ~2-3× tile size in RAM per worker, though the tag header already carries `data_offset`/`byte_length` | `data.fromfile(dmfile, array_length)` + in-place `byteswap()` on the full buffer | fixed | [#157](https://github.com/jamesra/nornir-review/issues/157) |
| C09-D001 | 09 | P2 | debt | `importers/idoc.py:274-275,489-496` | Two hardcoded artifacts in the main import path: a no-op stub (`i = 5`) swallowing unparseable section numbers, and a volume-name-specific (`'RC3' in FullPath`) mosaic invalidation hack | leaves `SectionNumber = 0` | fixed | [#156](https://github.com/jamesra/nornir-review/issues/156) |
| C09-D002 | 09 | P3 | debt | `importers/mdoc.py:77-84` | `subprocess.call(..., shell=True)` on an unquoted path (breaks on spaces; `subprocess` only in scope via a star-import), plus lowercase-only `.tif` globs | `cmd = "mrc2tif " + stNameFullPath + ...` | open | [#204](https://github.com/jamesra/nornir-review/issues/204) |

**Notes — Flip/Flop coordinate contract as found:** only the idoc importer implements the Utah convention end to end. It flops the pixels via `ConvertImagesInDict(Flip=Flip)` (`idoc.py:468`) and compensates in the coordinate write with `MosaicFile.Write(..., Flip=not Flip)` (`idoc.py:513`), with the reasoning in the comment at 511-512. Every other importer breaks the contract in a different direction: MRC flips pixels and never touches coordinates (C09-B001), PMG flips coordinates and never touches pixels (C09-B006), DM4 does neither despite accepting a `FlipList` (C09-B004). The contract is a per-file convention rather than a shared helper, which is exactly why each importer drifted independently — this is the concrete evidence for morning design theme 5, and the `Flip=not Flip` pairing is load-bearing and documented in only that one comment.

Generator hygiene is now good in the modern importers (idoc, mrc, dm4 all use `yield from` correctly). The remaining streaming problem is the opposite one: idoc materializes its section generator (C09-P001) and MRC queues per-tile tasks with no backpressure (C09-P002). `pmg.Import` and `sectionimage.Import` are still non-incremental — `pmg.Import` discards every `ToMosaic` return value, so VolumeData.xml is written once at the very end.

---

## Chunk 10 — Pyre UI + GL

Paths: `pyre/gl_engine/`, `pyre/views/`, `pyre/controllers/transformcontroller.py`, `pyre/commands/stos/`

**Invariants verified as holding:** only the source sub-view gets `warp_into_target_display=True` / `rigid_composite_source_align=True` (`compositetransformview.py:237-239`), the target layer is forced to static quads (`imagetransformview.py:192-205`), control-point drag genuinely patches instead of remeshing, and no CuPy array reaches an OpenGL call unconverted.

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C10-B001 | 10 | **P0** | bug | `commands/stos/translaterigidcommand.py:80`, used at `225` | Rigid drag cancel cannot undo the gesture: `_original_points` stores a **reference** to the live transform model, not a copy, and `Translate` mutates that same object in place — so right-click/cancel silently commits the misalignment | `self._original_points = transform_controller.TransformModel`; cancel reassigns the already-mutated model. Field is even annotated `NDArray[np.floating]` — **verified by hand** | fixed | [#9](https://github.com/jamesra/nornir-review/issues/9) |
| C10-B002 | 10 | P2 | bug | `commands/stos/translaterigidcommand.py:112-127` | Drag origin is re-derived **after** the transform mutates, so the screen→world mapping shifts mid-event and Source-panel drag tracking is not 1:1 | `get_world_positions` at 112, `Translate` at 123, `get_world_positions` again at 126 | wontfix (`4cefac1`) | [#158](https://github.com/jamesra/nornir-review/issues/158) |
| C10-B003 | 10 | P2 | debt | `views/gltiles.py:162` and `931` | Duplicate `_tile_bounding_rect` definition shadows the first, leaving three dead helpers that would raise if called; line 212 also does `np.concatenate(np.array(...), 2)` with a bogus positional axis | no callers of either helper | fixed (`f59af31`) | [#159](https://github.com/jamesra/nornir-review/issues/159) |
| C10-B004 | 10 | P2 | bug | `views/transformcontrollerview.py:224` | Staleness check compares XY-swapped GL buffer contents against YX controller points, so the early-out never fires and the whole control-point buffer re-uploads on every change | `PointView.points` setter applies `swap_columns_to_XY` (`pointview.py:142`) | fixed (`0cf9864`) | [#160](https://github.com/jamesra/nornir-review/issues/160) |
| C10-B005 | 10 | P2 | bug | `views/gltiles.py:245-266` | Half-texel handling offsets the tile texture by +0.5 px relative to geometry and makes the shared 4096 seam sample texel 4095 on one side and texel 0 on the other — a full-texel discontinuity | `(points_yx - BottomLeft + 0.5)/size` clamped to `[half_texel, 1-half_texel]` | open | [#161](https://github.com/jamesra/nornir-review/issues/161) |
| C10-B006 | 10 | P2 | bug | `gl_engine/context_aware_vao.py:294-306` | Per-context VAO leak: deletes are skipped when the context is not current but the dict is cleared unconditionally; the dict also pins `QOpenGLContext` objects, and `__del__` runs `cleanup()` under an arbitrary context | `clear()` outside the `if current_context == context` guard | fixed (`5c3dbb8`) | [#162](https://github.com/jamesra/nornir-review/issues/162) |
| C10-B007 | 10 | P2 | bug | `gl_engine/gl_buffer.py:117,219`; `framebuffer.py:126`; `shader_base.py:48,71,124` | GL objects are deleted from `__del__` with no guaranteed current context, so deletes land in whatever context is current or are swallowed; tile churn in `update_all_tile_buffers` relies on this | `glDeleteBuffers` inside `except Exception: pass` | fixed (`235ca8b`) | [#163](https://github.com/jamesra/nornir-review/issues/163) |
| C10-B008 | 10 | P2 | debt | `gl_engine/shaders/shader_base.py:89-95`; `texture_shader.py:106-123` | One module-level program plus cached attrib/uniform locations shared by every STOS panel — correct only if all `QOpenGLWidget` contexts share, unlike the explicitly per-context VAO handling elsewhere | `ContextAwareVAOHelper` keeps VAOs per context; `compositetransformview.py:414-418` re-inits "in this context" | fixed | [#164](https://github.com/jamesra/nornir-review/issues/164) |
| C10-B009 | 10 | P2 | bug | `controllers/transformcontroller.py:1580,1586,1619` | Rotation/scale pivots downcast to float32 while the comparable path at 1649 uses float64; at slice coordinates in the tens of thousands the pivot rounds by ~4e-3 px and accumulates over repeated scroll notches | `dtype=np.float32` vs `dtype=np.float64` | fixed | [#165](https://github.com/jamesra/nornir-review/issues/165) |
| C10-B010 | 10 | P2 | bug | `commands/stos/translatecontrolpointcommand.py:157` | Control-point drag repaints only the driving panel, so peer STOS windows stay stale until mouse-up — unlike the rigid path | rigid calls `repaint_peer_stos_gl_panels` at 130-131 | fixed | [#166](https://github.com/jamesra/nornir-review/issues/166) |
| C10-B011 | 10 | P2 | bug | `views/compositetransformview.py:241` | Sub-views capture `_repaint_callback` by value at creation (it is `None` in `__init__`), so budgeted/lazy mesh continuation frames are never requested for the source FBO | consumer is `imagetransformview.py:290-293` | fixed | [#167](https://github.com/jamesra/nornir-review/issues/167) |
| C10-B012 | 10 | P3 | bug | `gl_engine/shaders/texture_shader.py:52-61` | The interactive native-shift block is not gated on `use_rigid_path`, so a stale nonzero shift uniform also displaces mesh/grid tiles; the `> 0.001` test silently drops sub-milli-pixel shifts | lines 62 and 67 are gated, this one is not | open | [#205](https://github.com/jamesra/nornir-review/issues/205) |
| C10-B013 | 10 | P3 | bug | `views/gltiles.py:500-519` | Tile-edge samples merged with lattice coordinates by exact `np.unique`, so a control-point line within float noise of a 4096 boundary yields near-duplicate rows and zero-area triangles at the seam | downstream called with `require_valid_topology=False` (1013-1015) | open | [#206](https://github.com/jamesra/nornir-review/issues/206) |
| C10-P001 | 10 | P1 | perf | `views/gltiles.py:347-353` | Per-triangle Python loop validates Delaunay orientation on every cached-simplices vertex rebuild — interpreted O(triangles) work per tile per event, on the UI thread; fully vectorizable | `for tri in simplices: areas.append(...)` in `_triangle_orientations` | fixed (`c5bdc95`) | [#72](https://github.com/jamesra/nornir-review/issues/72) |
| C10-P002 | 10 | P2 | perf | `views/gltiles.py:424-448` | Lawson repair rebuilds the entire edge→triangle dict after **every single** flip (loop `break`s), up to 128 full O(triangles) rebuilds per tile | `while changed and flips < max_flips` | fixed | [#168](https://github.com/jamesra/nornir-review/issues/168) |
| C10-P003 | 10 | P2 | perf | `views/composite_display.py:404-417` | Full Nx4 control-point set pulled to host and copied on every composite draw — the host-array rule calls this out explicitly ("do not convert whole `TargetPoints` per mouse move") | `_as_numpy_f64(...).copy()` | fixed (`ca13e48`) | [#169](https://github.com/jamesra/nornir-review/issues/169) |
| C10-P004 | 10 | P2 | perf | `views/transformcontrollerview.py:320-328` | Composite display-row override does two full control-point buffer uploads plus two selection-texture writes per frame | override + `finally` restore, each hitting the `GLBuffer.data` setter | fixed (`ff1715c`) | [#170](https://github.com/jamesra/nornir-review/issues/170) |
| C10-P005 | 10 | P2 | perf | `views/gltiles.py:668,733` | Per-mouse-move patching copies each affected tile's whole Nx8 float32 vertex block and re-uploads the full buffer rather than the changed sub-range | `np.array(vertices, copy=True)` in both patch functions | wontfix (`835dd40`) | [#171](https://github.com/jamesra/nornir-review/issues/171) |
| C10-P006 | 10 | P3 | perf | `views/imagetransformview.py:712-713` | Module import executed inside the innermost per-tile draw loop every frame (also violates the imports-at-top standard) | `from pyre.image_contrast import ...` inside the `for ix/for iy` loops | open | [#207](https://github.com/jamesra/nornir-review/issues/207) |

**Notes:** Visual-only findings needing screenshot/plot triage under `NORNIR_HEADLESS=1` rather than pytest: C10-B005 (one-pixel seam line at 4096 boundaries plus a global half-pixel magenta/green misregistration), C10-B013 (folded triangles when a lattice line coincides with a tile edge), C10-B012 (mesh tiles displaced by a stale rigid shift), C10-B011 (source FBO left partly empty — magenta simply missing), and C10-B008 (garbage or blank second/third STOS panel). C10-B001, B002, B004, B009, B010 are all assertable without a GL context by driving the command/controller with fakes, in the style of `tests/test_tile_incremental_refresh.py`. Encapsulation risk not tabled separately: `composite_display.py:88-105,201-210,332-343` reads **and writes** `TransformController._cached_composite_*` private state, so the freeze/cache lifecycle is split across two modules with no single enforcement point.

---

## Chunk 11 — Build dashboard (nornir-builddashboard)

Paths: `nornir-builddashboard/nornir_dashboard` (`store.py` 583, `mqtt_subscriber.py` 526,
`main.py` 347, `config.py` 78, `ws_broadcast.py` 43), `nornir_dashboard/static/app.js` 1319,
`Dockerfile`. Reviewed as one chunk (~2.5 kLOC of Python) split into five sub-areas:
SQLite store, MQTT ingest/projection, FastAPI app + async lifecycle, config, and the static UI.

Unlike chunks 01-10 this package sits entirely off the science path — it observes builds and
never writes volume data — so there are **no P0 findings here**. The severity ceiling is P1
for silently dropped telemetry, an unauthenticated destructive endpoint, and the write
amplification that makes the dashboard the bottleneck during a log flood.

Existing tests: 45, of which 44 pass here (see C11-D004). Fourteen findings below were
confirmed by executing the code in this container, not by reading alone.

| ID | Chunk | Severity | Type | Location | Concern | Evidence | Status | Issue |
|----|-------|----------|------|----------|---------|----------|--------| --- |
| C11-B001 | 11 | P1 | bug | `mqtt_subscriber.py:465-475` | `_refresh_top_level_progress` sorts tracks on publisher-supplied `depth`; one track with `"0"` (string) beside `_update_progress`'s hardcoded `100` (int) raises `TypeError` mid-`_project_event`, so the pending `current_stage`/`section`/`element` write at 378-379 never runs, the event is never persisted, and nothing is broadcast — all swallowed by the blanket `except` in `_on_message:166` | **executed:** `TypeError: '<' not supported between instances of 'str' and 'int'` from `sorted(tracks.items(), key=sort_key)` | fixed | - |
| C11-B002 | 11 | P1 | bug | `store.py:194-198`, caller `mqtt_subscriber.py:200-202` | `update_run_fields` filters out `v is not None`, so no column can ever be set back to NULL. The stale-revival path explicitly passes `{"status": "running", "end_ts": None}` intending to clear the end time; the `None` is dropped and the revived run keeps its old `end_ts`, so the UI shows a `running` build that already ended and computes a wrong runtime | **executed:** after complete → revive, row is `status='running', end_ts=123.0` | fixed | - |
| C11-B003 | 11 | P1 | bug | `mqtt_subscriber.py:189` | `ts = float(payload.get("ts") or ...)` is unguarded and runs *before* any store write, so one malformed timestamp discards the entire message — no `last_seen`, no `error_count` increment, no event row, no broadcast. An `error` line with a bad `ts` is invisible in both the log pane and the sidebar counter | **executed:** `log/error` with `ts="not-a-number"` produced 0 SQL statements, 0 broadcasts, 0 stored events | fixed | - |
| C11-B004 | 11 | P1 | bug | `main.py:334` | `app = create_app()` at module scope opens SQLite and `os.makedirs` **at import time**, so merely importing the package creates `nornir-dashboard.db` in the current directory; `run()` then calls `load_config()` a second time, and a `config` passed to `create_app` by any other caller is ignored by the console script | stray `/workspace/nornir-dashboard.db` and `nornir-builddashboard/nornir-dashboard.db` both exist (gitignored via `*.db`) | fixed | - |
| C11-B005 | 11 | P1 | bug | `mqtt_subscriber.py:144-147` | `clear_retained` publishes at QoS 0 and ignores the returned `MQTTMessageInfo`, so the retained-clear is dropped silently when the broker link is down — and it clears only the `meta` leaf. Deleted and stale runs are then revived as `running` from broker retain on reconnect, which is exactly what `_stale_sweeper`'s docstring claims this prevents | no `wait_for_publish`/`rc` check; `_stale_sweeper:137-139` states the intent | fixed* | - |
| C11-B006 | 11 | P2 | bug | `main.py:122-129`, `142-171` | Both sweepers are `async def` but call synchronous SQLite directly on the event loop while holding the store lock; retention issues 2 statements + a commit **per expired run** inline, so a large sweep stalls every WebSocket client for its duration. The REST handlers are correctly plain `def` (FastAPI threadpool), which makes the sweepers the outlier | no `asyncio.to_thread`; `_run_retention_sweep:110-114` loops `_delete_run_and_notify` | fixed | - |
| C11-B007 | 11 | P2 | bug | `config.py:71-73` | `retention_sweep_interval` is read with no positivity guard while `stale_sweep_interval` two lines up uses `_positive_or_default`; `NORNIR_DASHBOARD_RETENTION_SWEEP_INTERVAL=0` turns `_retention_sweeper` into `await asyncio.sleep(0)` — a tight loop hammering SQLite at 100% CPU | asymmetry with `config.py:62-67` | fixed | - |
| C11-B008 | 11 | P2 | bug | `main.py:228-230` | `/api/runs?limit=` is passed to SQL unvalidated; SQLite treats `LIMIT -1` as unlimited, so `?limit=-1` dumps the whole `runs` table. The events endpoint clamps via `clamp_events_limit`, this one does not | **executed:** `list_runs(limit=-1)` returned all rows, `limit=2` returned 2 | fixed | - |
| C11-B009 | 11 | P2 | bug | `store.py:56-67` | `parse_types_param` returns `None` (= all types) for an empty string but `[]` (= match nothing) when every requested key is unknown, and `_types_sql([])` emits `0=1`. A typo'd or renamed UI filter key silently yields an empty log view instead of falling back to all | **executed:** `parse_types_param("bogus") == []`, `parse_types_param("") is None` | fixed | - |
| C11-B010 | 11 | P2 | bug | `mqtt_subscriber.py:254` with `store.py:70-95` | `_classify` maps any unrecognized topic leaf to `kind='other'` and `_should_persist_event` stores it, but `_types_sql` has no branch for `other` — those rows are invisible under every UI filter and excluded from any filtered export, while still consuming the `prune_events` budget that protects real errors | **executed:** leaf `telemetry/gpu` stored as `kind='other'`; the 6-type clause contains no `other` predicate | fixed | - |
| C11-B011 | 11 | P2 | bug | `main.py:310-321` | The WebSocket handler unregisters only in `except WebSocketDisconnect` / `except Exception`; `asyncio.CancelledError` is a `BaseException`, so on server shutdown or task cancellation the socket is never removed from `_clients` and leaks into subsequent broadcasts. Belongs in a `finally` | both handlers are `except` clauses | fixed | - |
| C11-B012 | 11 | P2 | bug | `store.py:192-213` | `update_run_fields` never checks `rowcount`, so an UPDATE against a run the sweeper just deleted is a silent no-op. Combined with retention/stale deletes running concurrently with the MQTT thread, in-flight projections vanish with no log line | **executed:** update on an unknown `run_id` raised nothing | fixed | - |
| C11-B013 | 11 | P2 | bug | `mqtt_subscriber.py:128-137` | `stop()` clears `_started` and sets `_stop_event` but never joins `_connect_thread`; the window between a successful `connect()` (112) and `loop_start()` (113) is unguarded, so a connect in flight can start a paho network thread *after* shutdown. Daemon threads mean this leaks per `create_app` rather than blocking exit | no `join`; `loop_stop`/`disconnect` may run before `loop_start` | fixed | - |
| C11-B014 | 11 | P2 | bug | `mqtt_subscriber.py:408-456`, `381-406` vs `store.py:293-310`, `339-394` | `_merge_progress_track`/`_merge_pool_track` do a read-decode-mutate-reserialize-write cycle on the tracks blob with no transaction spanning it, so the MQTT thread races `clear_run_progress` / `mark_stale_runs` on the loop: a merge that read before the clear rewrites the cleared tracks back | `get_progress_tracks` then `update_run_fields` are separate lock acquisitions | fixed | - |
| C11-B015 | 11 | P2 | bug | `mqtt_subscriber.py:339-356` | `stage_failed` updates `current_stage` but neither sets the run status to `failed` nor increments `error_count`, so a failed stage keeps the run rendering as `running` until an unrelated `meta` message happens to correct it | `event_type in ("stage_start", "stage_end", "stage_failed")` share one branch with no status write | fixed* | - |
| C11-B016 | 11 | P3 | bug | `config.py:45-73` | Every `int()`/`float()` env read is unguarded, so a malformed `NORNIR_MQTT_PORT` or `NORNIR_DASHBOARD_RETENTION_DAYS` kills startup with a bare traceback. Only the two stale values get validated, and only for positivity, not parseability | `_positive_or_default` receives an already-parsed float | fixed | - |
| C11-B017 | 11 | P3 | bug | `main.py:323-326` vs `328-329` | `index()` returns `FileResponse(.../index.html)` unconditionally while the `/static` mount right below it is guarded by `os.path.isdir`; a packaging miss that drops `static/` yields a 500 on `/` rather than a clear startup failure | asymmetric guard | fixed | - |
| C11-P001 | 11 | P1 | perf | `mqtt_subscriber.py:191-227` with `store.py` commit-per-call | Each MQTT message costs 3-4 separate transactions because every store method commits individually, and the connection runs at SQLite defaults (`journal_mode=delete`, `synchronous=FULL`) — so a single log line is 3 fsyncs. This is the dashboard's dominant cost under the `iterate_progress` floods the store's own comments cite; needs one transaction per message plus WAL + `synchronous=NORMAL` | **executed** statement counts per message: `log/info` = 2 INSERT, 1 UPDATE, 1 SELECT, **3 COMMIT**; `log/error` = **4 COMMIT**; `event:iterate_progress` = 1 INSERT, 3 UPDATE, 4 SELECT, **4 COMMIT** | fixed | - |
| C11-P002 | 11 | P2 | perf | `mqtt_subscriber.py:192` | `update_run_fields(run_id, {"last_seen": now})` fires immediately after `ensure_run`, whose `ON CONFLICT(run_id) DO UPDATE SET last_seen=excluded.last_seen` (`store.py:186`) already wrote exactly that value — one wholly redundant UPDATE + commit on every single message | **executed:** confirmed in the per-message counts above | fixed | - |
| C11-P003 | 11 | P2 | perf | `mqtt_subscriber.py:197-202` | The stale-revival check calls full `get_run` on every non-terminal message purely to read one column, and `_decode_run_row` `json.loads` both `progress_tracks` and `pool_tracks` on the way out. Should be `SELECT status WHERE run_id=?` | 23-column row + 2 JSON parses per message | fixed | - |
| C11-P004 | 11 | P2 | perf | `mqtt_subscriber.py:408-456` | Progress merging decodes the entire tracks blob, copies the dict, and reserializes and rewrites the whole row on every progress event — and `_refresh_top_level_progress` re-reads it straight afterwards. Track count is unbounded within a stage, so cost grows with distinct labels | **executed:** one `iterate_progress` message = 4 SELECTs, 3 UPDATEs | fixed | - |
| C11-P005 | 11 | P2 | perf | `main.py:70-79` | `_send_to_clients` awaits `client.send_json` serially with no timeout, so a single stalled browser blocks every other client's frames and the drain loop behind it — classic head-of-line blocking. Needs per-client queues or `asyncio.gather` with a send timeout | `for client in list(self._clients): await client.send_json(message)` | fixed | - |
| C11-P006 | 11 | P2 | perf | `store.py:452-455` | The `q` filter is `lower(COALESCE(payload,'')) LIKE '%...%'`, a full scan of `events` with no FTS index, and `iter_events_for_export` repeats it for every export batch. Only `idx_events_run(run_id, id)` exists | no FTS5 table; LIKE cannot use the index | verified* | - |
| C11-P007 | 11 | P3 | perf | `main.py:48`, `ws_broadcast.py:15-29` | `asyncio.Queue()` has no `maxsize` and `coalesce_broadcast_messages` merges without a cap, so a flood while the loop is busy grows the queue unboundedly and then emits one enormous `event_batch` frame | no bound in either place | fixed | - |
| C11-P008 | 11 | P3 | perf | `store.py:322-337`, `360-367` | Both sweep queries filter on `COALESCE(last_seen, first_seen, 0)` with no index on `runs`, so each sweep is a full table scan. Harmless at a few hundred runs, but the retention window is 30 days by default | only the events index is created | fixed | - |
| C11-S001 | 11 | P1 | security | `main.py:237-243`, `config.py:51`, `Dockerfile:9` | There is no authentication or authorization on any endpoint, `DELETE /api/runs/{run_id}` permanently destroys a run's history **and** publishes a retained MQTT clear, and the default bind is `0.0.0.0` in both the config default and the image `ENV`. Any host that can reach the port can delete build history and mutate broker retained state | no dependency/middleware performs auth anywhere in `create_app` | fixed | - |
| C11-S002 | 11 | P2 | security | `Dockerfile` | No `USER` directive, so the network-exposed web service runs as root inside the container; `/data` is also created root-owned, which breaks a bind mount owned by another uid | image ends at `CMD` with no user drop | fixed | - |
| C11-D001 | 11 | P3 | debt | `store.py:107`, `119`, `413-419` | `_events_since_prune` is keyed by `run_id` and never cleaned by `delete_run`, the stale-stub delete, or retention, so the dict grows for the process lifetime | **executed:** key `'gone'` still present after `delete_run('gone')` | fixed | - |
| C11-D002 | 11 | P3 | debt | `config.py:53-55` | `NORNIR_DASHBOARD_MAX_EVENTS` defaults to `0`, which disables `prune_events` entirely — the flood protection the store is built around (and whose `_PRUNE_EVERY` batching exists to make cheap) is off unless explicitly configured, leaving 30-day retention as the only bound on table growth | `max_events_per_run <= 0` returns early in `prune_events:524` | mitigated* | - |
| C11-D003 | 11 | P3 | debt | `static/app.js:1162-1168`, `737` | `escapeHtml` does not escape `'`; every current interpolation happens to sit in a double-quoted attribute or a text node, so this is latent rather than live, but one single-quoted attribute added later becomes stored XSS from build log text. `fmtTime(event.ts)` at 737 is also the one unescaped interpolation among its escaped siblings | helper replaces only `& < > "` | fixed | - |
| C11-D004 | 11 | P3 | debt | package-wide | `fastapi`/`uvicorn` are not installed in the Nornir devcontainer, so `tests/test_retention.py` cannot even be collected there (44 of 45 tests run) — this package has effectively no test signal in the standard environment, and C11-B004 means the import that fails also would have created a DB file | `ModuleNotFoundError: No module named 'fastapi'` at collection | fixed* | - |
| C11-D005 | 11 | P3 | debt | `main.py:341`, `config.py:6-9` | The dashboard uses `logging.basicConfig` and module loggers rather than `nornir_shared.misc.SetupLogging` / `NORNIR_LOG_ROOT`, so it is the one Nornir service outside the unified logging convention. The tradeoff is real — the Dockerfile deliberately avoids depending on the monorepo to keep the image small — so this needs an explicit decision rather than a silent deviation | Unified-Logging-Convention rule vs `Dockerfile:2-3` | fixed | - |
| C11-D006 | 11 | P3 | debt | `Dockerfile:20-21` | `pip install .` with unpinned `fastapi >= 0.110` / `uvicorn >= 0.29` / `paho-mqtt >= 2.1.0` means two builds of the same commit can ship different dependency trees, and there is no `HEALTHCHECK` for Compose to gate on | no constraints file, unlike `constraints-headless.txt` elsewhere in the repo | fixed | - |

**Notes:** The static UI was reviewed for injection sinks specifically: `app.js` routes untrusted
run and log text through `escapeHtml` at every `innerHTML` site (264, 407-435, 498, 736), and the
numeric interpolations use `toFixed`, so there is **no live XSS** — C11-D003 is about the helper
being one edit away from failing, not a current hole. The sidebar does assume
`progress_fraction` is numeric (`pct.toFixed(1)`); because `update_run_fields` writes
`payload["fraction"]` unvalidated and SQLite stores a non-numeric string as TEXT in a REAL
column, a malformed publisher value would reach `toFixed` as a string and throw during render.
That chain is unverified end to end and is folded into C11-B016's validation gap rather than
tabled separately. C11-B001, B002, B003, B008, B009, B010, B012 and P001-P004 are all
assertable in the existing pytest style without a broker or a browser — `tests/test_mqtt_subscriber.py`
already drives `_handle_message` directly, which is how the confirmations above were produced.

**Resolution (all 33 chunk 11 findings addressed; dashboard suite 152 passing).** New coverage
lives in `tests/test_config.py`, `tests/test_store_chunk11.py`,
`tests/test_mqtt_subscriber_chunk11.py`, `tests/test_app_chunk11.py`, and
`tests/test_logging_setup.py`. Five rows resolved differently than the finding text proposed,
marked `*` above:

* **C11-B005** — only the `meta` leaf is published with `retain=True` by
  `nornir_shared.mqtt_telemetry`, so a meta-only clear is correct; the real defects (QoS 0 and the
  ignored `MQTTMessageInfo`) are fixed, and `clear_retained` now returns success.
* **C11-B015** — `stage_failed` now sets `status='failed'`, but deliberately does **not** increment
  `error_count`: `PipelineManager` logs the same failure through `logger.error` immediately before
  publishing the event, which already increments the counter.
* **C11-D002** — the `0` default is kept because `tests/test_events_query.py::TestMaxEventsDefault`
  encodes "unlimited by default" as a contract. Negative values now normalize to `0`, and startup
  logs which bound (retention or nothing) actually applies. **Open question:** should the default
  become a finite bound?
* **C11-P006** — no FTS5 table was added. The search predicate always carries `run_id = ?`, so
  `EXPLAIN QUERY PLAN` shows `idx_events_run` narrowing the scan to one run rather than the whole
  table (asserted in `TestEventSearchStaysRunScoped`). The finding's "full scan of `events`" is
  therefore overstated; FTS5 would double storage for a per-run scan. **Open question:** revisit if
  a single run exceeds ~1M events.
* **C11-D004** — `fastapi`/`uvicorn` still are not in the devcontainer image; the tests now skip
  cleanly instead of failing collection, and a `[test]` extra pins what is needed.

`C11-S001` gained an opt-in token (`NORNIR_DASHBOARD_TOKEN`) on `/api/*` and `/ws`, a loopback
default bind, and `NORNIR_DASHBOARD_ALLOW_DELETE`; `/`, `/static/*`, and the new `/api/health`
stay ungated so the page can load and Docker can probe. `C11-D005` is resolved by delegating to
`nornir_shared.misc.SetupLogging` when `NORNIR_LOG_ROOT` is set and the package is importable,
falling back to stdout in the standalone image — so the convention applies wherever it can.

---

# Summary

## Counts

| Severity | Count |
|----------|-------|
| P0 (data loss / wrong science) | 10 |
| P1 (silent wrong output) | 70 |
| P2 (perf / ops pain) | 115 |
| P3 (maintainability / debt) | 46 |
| **Total** | **241** |

By type: 133 `bug`, 67 `perf`, 15 `parity`, 24 `debt`, 2 `security`.
All 10 core chunks reviewed, plus chunk 11 (builddashboard) added 2026-08-29. 28 findings carry
status `confirmed` — nine were re-read at the cited line, five were verified by the chunk 01-10
passes themselves, and the 14 chunk-11 items were confirmed by executing the code.

## The 10 P0s

| ID | Location | One line |
|----|----------|----------|
| C03-B001 | `local_distortion_correction.py:4175` | Pooled STOS path omits `peak_ratio`, silently disabling every false-peak reject gate — **fails open** |
| C05-B001 | `nearest_neighbor.py:72-81` | Live sibling of the just-fixed `cdist` strided-view bug; CuVS reads packed garbage above 4096 points |
| C07-B001 | `pyramidlevelhandler.py:70-77` | `GetScale()` never advances its loop variable — guaranteed build hang |
| C07-B002 | `channelnode.py:78-84` | `ChannelNode.Scale` always returns `None`; scale metadata invisible to every consumer |
| C07-B003 | `mosaicbasenode.py:48-57` | Checksum getter writes `attrib` without marking dirty — computed checksum silently discarded |
| C08-B001 | `block.py:3414-3422` | NaN compose failure hard-aborts the SliceToVolume stage instead of skipping the hop |
| C08-B002 | `stosfile.py:1168-1170` | Composition raises on its own output text, so one unmapped grid point kills the hop |
| C09-B001 | `mrc.py:340` | MRC flips tile pixels but never the mosaic coordinates; `FlipList` ignored entirely |
| C10-B001 | `translaterigidcommand.py:80` | Rigid drag cancel restores a live reference, so right-click never undoes the translate |
| C00-P001 / C01-P001 | `checksum.py:64` | `FileChecksum` reads whole files into RAM (carried P0 from the overnight review) |

## Summary sections below describe the review as filed

The three sections that follow — top correctness risks, top performance wins, and the
recommended fix order — record the state at the end of the review pass and are kept as written
for context. They are **no longer a to-do list**: 39 of the 42 findings they cite are now `fixed`
or `wontfix`. The three still open are **C01-P005** (`print()` sites onto unified logging),
**C02-P006** (per-angle device→host syncs) and **C07-P002** (`ProcessIterateNode` materializes
every candidate). Work the tables, not these lists.

## Top 5 correctness risks

1. **Gates that fail open.** C03-B001 and C07-B005 both make a check pass by construction (`peak_ratio=None` → not ambiguous; a `(bool, reason)` tuple → always truthy). These produce plausible-looking wrong science with no error, which is the worst failure mode in the repo.
2. **The Flip/Flop contract is unwritten and three importers disagree.** C09-B001, C09-B004, C09-B006: idoc alone pairs "flop the image" with "negate Y in the mosaic". MRC does half of it, PMG does the other half, DM4 does neither. This is the concrete case for morning design theme 5.
3. **Strided views reaching CuVS.** C05-B001 is the same class as the bug fixed last week; `cp.asarray` normalizes dtype but not strides, and every control-point caller passes an `(N,4)[:, 2:4]` view.
4. **Save-on-read and dirty-flag escape hatches in the volume XML.** C07-B006 makes `findall` write VolumeData.xml during a read, C07-B007/B008 add nodes as a side effect of a getter, and C07-B003/B009 mutate without marking dirty. Together these mean a read-only traversal can alter metadata while a real change can be lost.
5. **NaN treated as fatal where the design says fall back.** C08-B001/B002/B007 abort whole stages on unmapped points that the RBF fallback exists to fill — and C08-B003's substring classifier can trigger that abort on an unrelated error containing "info".

## Top 5 performance wins

1. **`get_runtime_config(refresh=True)` per cell** (C03-P001) — clears the `lru_cache` and re-reads ~14 env vars twice per cell measurement. A per-pass snapshot removes tens of thousands of `os.environ` lookups per pass. Cheapest large win in the review.
2. **Vectorize `_triangle_orientations` and bound the Lawson repair** (C10-P001, C10-P002) — interpreted per-triangle work on the UI thread during mouse-move, plus up to 128 full dict rebuilds per tile.
3. **Bound in-flight tiles in the three ungated paths** (C04-P001, C08-P001, C09-P002) — `TilesToImageThreaded`, `MosaicToVolume`, and the MRC importer each queue one task per tile for a whole section. At the documented 2-3 GB/core envelope a 100-tile section is already ~3 GB of in-flight buffers.
4. **Stream `FileChecksum` and stop materializing generators** (C01-P001, C07-P002, C09-P001) — chunked hashing plus removing three `list(generator)` calls that defeat incremental designs the code already has.
5. **Stop the redundant recomputation in relaxation and `findall`** (C06-P001 ~3× tension work in an acknowledged bottleneck; C07-P001 triple XPath scan per call, with the middle loop discarding its result).

Also worth a single sweep rather than point fixes: the per-cell and per-angle device→host syncs (C02-P003, C02-P006, C03-P002, C04-P004) and the float64 upcasts in batched paths (C02-P001, C03-P004).

## Recommended fix order

**Wave 1 — hangs and fail-open gates (small diffs, large blast radius).** C07-B001 (one-line loop variable), C07-B002 (`hasattr` guard), C03-B001 (one missing kwarg), C05-B001 (`ascontiguousarray`, mirroring `spatial_distance.py:94`), C10-B001 (copy instead of reference), C07-B005 (unpack the tuple). Each is a few lines; together they close five of the ten P0s. Add a >=4096-point regression test for C05-B001 modeled on `test_cupy_cdist_strided_view_matches_contiguous`.

**Wave 2 — stop destroying or silently corrupting output.** C08-B001/B002/B007 (make output-side non-finite a per-slice skip, per the stated design intent) with C08-B003 (replace the substring classifier with a typed exception). C07-B003/B009 (dirty-flag escape hatches). C04-B001/B002 (`TransformStos` and the argument-dropping wrappers). C08-B004 (mosaic saved valid after a swallowed per-tile failure).

**Wave 3 — the Flip/Flop contract.** Write the axis/origin contract as a shared helper plus one golden fixture test, then fix MRC, PMG, and DM4 against it (C09-B001, B002, B004, B006). Doing these individually risks trading one Y-shift for another, so the contract should land first.

**Wave 4 — memory and throughput.** Wave-1-cheap perf items in the order above, with the in-flight gates (C04-P001, C08-P001, C09-P002) prioritized because they are the ones that fail outright on a large section rather than merely running slowly. Per the Serial-batched-primitives rule, any refine perf claim needs sign-off on a >=100-tile section.

**Wave 5 — parity and debt.** Add the four twin-drift items (C05-B002, B005, B006, B012) to `docs/cpu_gpu_dual_class_parity.md`; fix the serial/batched validity-gate and dtype divergences (C02-B003, C02-P001); sweep the `print()` and no-op-`Warning` sites onto unified logging (C02-B012, C06-B012, C01-P005/P006).

**Wave 6 — dashboard (independent of waves 1-5; nothing here touches the science path).** Order within the chunk: C11-S001 first (an unauthenticated `DELETE` on `0.0.0.0` is the only finding an outsider can trigger), then the three silent-telemetry-loss bugs C11-B001/B002/B003 — each is a few lines and each is already reproducible via `_handle_message` in the existing test style. Then C11-P001/P002/P003 as one commit: a single transaction per message plus WAL, dropping the redundant `last_seen` UPDATE and narrowing the stale check to one column, which together remove roughly three quarters of the per-message SQL. Fixing C11-B002 (the `None`-drop) requires deciding whether `update_run_fields` should distinguish "not supplied" from "set to NULL"; a sentinel is the smaller change, but every caller passing `payload.get(...)` then needs review, so land it with tests rather than as a drive-by.

## Caveats

- Findings are from static reading plus targeted verification, not from a full test run. Items marked `confirmed` were re-read directly at the cited line; items marked `open` are well-evidenced but unexecuted, and a few (notably the `UnboundLocalError` and `AxisError` classes in chunk 06) may sit on paths that are unreachable in current configurations. Each should be confirmed with a test before a fix lands.
- Chunk 10 pytest coverage is not in CI, and five chunk-10 findings are visual-only; a green pytest run there is not evidence of correctness.
- Chunk 11 (builddashboard) was reviewed on 2026-08-29 after the original pass. It is the only chunk whose findings were confirmed by execution rather than reading, which is why its `confirmed` ratio is much higher than chunks 01-10 — that reflects reviewing method, not relative code quality.
- The remaining optional infra (Docker images, `nornir-web`, `nornir-volumecontroller`/`nornir-volumemodel`) is still unreviewed, per the plan's deferral of infra.
