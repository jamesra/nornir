# Overnight bug-review progress (session started ~2026-08-09)

## Fixed this session

### nornir-shared
- **GenNameFromDict**: list mangling dropped entries (`value[1:-1]` + overwrite). May change pipeline mangled names for list params.
- **ListFromDelimited**, image magick helpers, MQTT debug file location (NORNIR_LOG_ROOT/temp).
- **files.RecurseSubdirectories**: path doubling (`fullpath = d.path`); bare except → OSError.
- **IsOutdated**: pass `comparison` through to `NewestFile`.
- **AreValidImages**: join `ImageDir` for single-file case.
- **FileChecksum**: open binary `'rb'` (checksums change vs old text mode / CRLF).
- **TryRemoveMinValueOutlier** / **TryRemoveMaxValueOutlier**: guard short histograms; stop when no trim target (no infinite loop / IndexError).
- Tests: `test_misc_helpers.py`, `test_Histogram.py` passed.

### nornir-pools
- Task abstract `NotImplementedError`; **shared_memory** address round-trip via `repr`/`literal_eval`.
- **poolbase.remove_finished_threads**: include index 0 (`range(..., -1, -1)`).
- **ProcessPool.add_task** returns task; **ImmediateProcessTask** no Popen in `__init__`; returncode + CalledProcessError; worker `queue.Empty` only.
- Multiprocess: register tasks before `apply_async`; shutdown waits then close/join.
- Pool tests passed (33 passed / 9 skipped with shared/stos).

### nornir-imageregistration
- STOS/mosaic GetInfo exception types; CompressedTransformString strip bug; cache/permutation excepts.
- **STOS Windows path rebase**: was skipped on Windows because `os.path.isabs(Y:\...)` short-circuited before rebase — fixed. `test_stosfile_paths.py` 21 passed.
- **FindDuplicateFixedPoints**: `epsilon` parameter was ignored (`distance <= 0`); now `distance <= epsilon` (CPU + GPU bases).
- **FlipWarped**: restore both axes (`temp + flip_center`) in triangulation + landmark (was X-only restore → permanent Y shift).
- **RemoveDuplicateControlPoints**: was comparing enumerate indices, never dropped coordinate duplicates — now `np.unique` on rounded fixed (y,x).
- **FindDuplicates**: 1-D bool mask (was `(1, N)`); set-based fixed-space match.
- **phasecorrelation cutoff_percent**: stop double `* 100` (percentiles already 95–100).
- **Refine fallback** (`WeightMethod.Registration`): take strongest scores (`[-num_needed:]`), not weakest.
- **StosFile.Create**: set control/mapped masks independently when non-None.
- **PIL leaks**: histogram path + `SaveImage_JPeg2000` use context managers.
- **GPU ControlPointBase.points setter**: `EnsurePointsAre4xN_CuPyArray`.
- **nearest_neighbor SciPy path**: output backend follows query array via `cp.get_array_module`, not global `UsingCupy()`.
- **stos_brute pad_and_rotate**: typo `orginal_shape` → `original_shape` (now passes pre-rotate shape into pad; previously left `None` so pad used rotated shape).

### nornir-buildmanager
- Gamma/histogram/pyramid/serialem/xelementwrapper: tighter exception types.
- **MDoc ToMosaic**: default extension `mdoc`; `yield from` parent idoc importer with converted idoc path (was discarded generator + dir path); broader tiff glob fallback.
- **`_SaveNodes`**: treat `ElementTree.Element` as a single node (was iterating children).
- **MappingNode.Mapped**: set `_AttributesChanged` on attrib write/clear; **StosMap** uses `len(mapping_node.Mapped)`.
- **BlockNode.NonStosSectionNumbers** getter: `find` only (no create-on-read).
- **TryAddLogs**: do not return early when first log is current — still parse / process remaining.
- **VikingXML Notes**: drop duplicate `append` after `SubElement`.
- **StosBrute**: remove CWD-relative `makedirs(OutputStosGroupName)`.
- Tests: `test_import_volumedata_save` + `test_no_delete` 24 passed.

## Session complete (~12:08 local, deadline 12:22)
Overnight bug review stopped at the deadline window. No further 45‑minute heartbeats.

**For morning:** skim behavioral notes below before shipping volumes; open design plan at `.cursor/plans/morning_design_improvements_2026-08-09.plan.md`. Uncommitted fixes span shared/pools/imageregistration/buildmanager — commit only when explicitly asked.

## Still open
- (Cleared) PP ActiveJobCount leak if remote callback never fires — morning design theme 3: bounded secondary wait + unwind + `tests/test_parallelpython_callback_timeout.py`.

## Passes 2–7 (summary)
- DM4 context open; StosBrute filter `list()`; O_EXCL locks; mosquitto PIPE/config; PP JobCountLock; ProcessOutputInterceptor wait; deleted duplicate peak_uniqueness.
- IsSequence; MosaicFile ImageSize; MRC gettempdir; Evaluate PostCmd log; morning design plan.
- StosMap filter/RemoveMapping(None)/AllowDuplicates/Compressed; Element sort; MosaicFile 2-tile; ControlPointBase.Flip (+ GPU).
- AreValidImages basenames; set.add (RT + tile_overlap); lock handle close.
- MaxNonEmptyBin; histogram parser index 0; prune ReadPruneMap assign; mdoc file init; SetLocked bool(int).
- MosaicChecksum warn not raise; path_entry_count OSError; rmtree single executor; MultiprocessThreadTask *args.

## Pass 9 (~08:23 wake)
- **Histogram.XAxis_Extrema_Using_Threshold**: use `max_index` (was always last bin).
- **im_histogram_parser**: slice intensity tuple from `parts[1]`, not `parts` list.
- **AreValidImages** single-file: skip `.npy` like the multi-file path.
- **MappingNode.__str__**: stop clearing `_mapped_cache` as a side effect.

## Pass 10 (~09:09 wake)
- **NearestSection**: empty → None; single frozenset/set via `next(iter(...))`.
- **try_locate_file**: drop spurious `self` parameter.
- **RemoveInvalidImageFile**: return False when `os.remove` fails.

## Pass 11 (~11:22 wake)
- **NearestSection**: seed distance with `inf` (negative reqnumber was broken).
- **Histogram.Mean**: return None when empty bin range (no ZeroDivision).
- **MosaicFile.Write** docstring: Flip=Y / Flop=X to match code.

## Morning behavioral notes
1. GenNameFromDict list fix → possible rebuilds for list-valued mangled stages.
2. CompressedTransformString trailing-space strip → possible checksum changes.
3. FileChecksum binary → checksum changes vs old text mode.
4. STOS rebase on Windows when Y: exists but `.stos` lives elsewhere → intentional remapping.
5. RemoveDuplicateControlPoints now actually dedupes → transforms with coincident fixed points change.
6. Refine fallback ranking fix → different control-point sets when cutoff fails to yield enough points.
7. stos_brute original_shape typo fix → pad overlap sizing uses pre-rotation shape when angle ≠ 0.
8. DataChecksum list length-prefix → mosaic/transform list checksums change; expect meta invalidation/rebuild.

## Theme 4 — memory-bounded I/O inventory (morning design)

Prioritized tickets from streaming rule
(`.cursor/rules/Streaming-and-memory-bounded-processing.mdc`). Mark **accept**
only when size is provably small or algorithm requires a global pass.

| Priority | Hot path | Package | Status | Notes / ticket direction |
|----------|----------|---------|--------|--------------------------|
| P0 | `FileChecksum` → `f.read()` entire file | nornir-shared | **reject full load for large mosaics/stos** | Stream in chunks into hashlib; keep binary mode. Add threshold or always stream. |
| P0 | Mosaic / transform list `DataChecksum` materializing whole lists | nornir-shared / buildmanager | **accept for metadata-sized lists**; reject if lists embed image bytes | Prefer paths + incremental checksums. |
| P1 | `assemble.TransformImage` / full-section assemble buffers | nornir-imageregistration | **reject for production full sections** | Prefer optimized tileset path (`AssembleTilesetNumpy`) + memmap spill. |
| P1 | `assemble_tiles` in-memory output before write | nornir-imageregistration | **accept with memmap** when `_use_memmap` | Keep memmap / temp-dir patterns; gate concurrency. |
| P1 | `ConvertImagesInDict*` loading many tiles | nornir-imageregistration | **reject unbounded dict** | Bound in-flight tiles; path handoff to workers. |
| P2 | `mosaicvolume` helpers loading full mosaic files into pools | nornir-buildmanager | **reject** | Pass mosaic paths; stream tile jobs. |
| P2 | Import idoc tile convert | nornir-buildmanager | **accept with generators** | Already yields per unit to `_SaveNodes`; keep path-based tile convert. |

Good patterns to keep: Import generators + `_SaveNodes`, `np.memmap` /
`memmap_metadata`, path/metadata across process boundaries, `ReleaseStagePools`
backpressure at stage boundaries.
