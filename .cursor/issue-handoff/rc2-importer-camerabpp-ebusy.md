# RC2 import on Build2: -CameraBpp with crushing, EBUSY retry, histogram speed (2026-11-05)

Reported by Build2: Host while importing RC2 raw sections (1226, 139, 360, 943_Redo) from `/backup1/RawData/RC2`.
All changes are **uncommitted** in `nornir-buildmanager` and `nornir-imageregistration` (shared checkout; for James).

## 1. -CameraBpp is ignored (with a warning) unless -NoCrush

- `importers/shared.py`: `CameraBppForImport(camera_bpp, no_crush)` returns the value for -NoCrush imports and
  `None` otherwise, logging "-CameraBpp N is ignored: it only applies to legacy (-NoCrush) imports...".
- `importers/idoc.py` and `importers/mrc.py` `Import()`: call it right after reading CameraBpp/NoCrush.
- `config/Pipelines.xml`: -CameraBpp help for ImportIDoc and ImportMRC says "Legacy (-NoCrush) imports only ...
  ignored with a warning unless -NoCrush is set"; the ImportIDoc epilog no longer shows `-CameraBpp 14` on a crushed import.
- Note: 8-bit sources are never crushed; dropping CameraBpp there changes nothing (8-bit data cannot exceed it).

### What CameraBpp did to a crushed import (answer for RC1_Crush, imported with -CameraBpp 14)

Crushed code = `floor((raw - offset) / step)` clipped to `2**bits - 1` (`noise_crush.crush`).
- **sigma**: estimated from the sampled raw tiles (`GetSectionNoise`). CameraBpp never reaches it.
- **step** = `max(1, round(k * sigma))`. Unaffected.
- **offset**: 0 for unsigned data; `floor(sample_min)` (if negative) for signed MRC data, from the noise sample. Unaffected.
- **bits**: from `section_max = max(noise sample max, upper edge of the section histogram's top occupied bin)`
  (`SectionCrushParams`). CameraBpp sets the histogram's value range (IDoc: `MaxVal` clamp; MRC: `bpp`, so 0..16383
  with 8-count bins instead of 0..65535 with 32-count bins), and `numpy.histogram` drops values outside the range.
  So **bits is the only crush parameter CameraBpp can change**, and only when (a) raw values exceed `2**CameraBpp - 1`
  outside the sampled tiles, or (b) the section maximum sits within one bin width (8-32 counts) of a `256 * step`
  boundary. When bits are equal, every tile code is identical.
- Also changed: the filter's contrast hints (`FilterMin/FilterMax` in code units, metadata only) and the histogram plot.
- Proof: `nornir-buildmanager/tests/importers/test_camera_bpp_crush.py` (in-range data: identical params and codes
  with and without the clamp; a hot value of 40000 in an unsampled tile: same sigma/step/offset, bits 8 vs 9, and only
  that one pixel's code differs).

**RC1_Crush verdict:** no reimport needed for a section whose `CrushBits` is 8 and whose raw maximum, divided by its
`CrushStep`, is at most 255 (then a no-CameraBpp import gives the same bits, so identical tiles). Only sections where
raw data exceeds 16383, or sits right at the 8-bit boundary, could differ, and then only in pixels above the camera
range. Check per section from the filter's `CrushStep`/`CrushBits` attributes and the MRC header max (or the
section histogram) before reimporting anything.

## 2. EBUSY/EAGAIN retry on raw reads

- New `nornir_imageregistration/io_retry.py`: `call_with_io_retry(read, attempts, base_delay, ...)` retries OSErrors
  with errno EAGAIN/EWOULDBLOCK/EBUSY with doubling delays, re-raises anything else at once.
- `noise_crush.load_raw_tile`: 5 attempts, 0.5 s doubling (7.5 s worst case). Covers the noise sample
  (`GetSectionNoise`) and every crushed tile conversion (`crush_tile_to_file` reads through it).
- `image_stats.__HistogramFileSciPy__` (the IDoc histogram pass): same retry.
- Not changed: `core/_core._LoadImageByExtension` already had its own loop (6 tries, 0.05 s doubling, ~1.6 s), used by
  legacy -NoCrush conversion. It could call the new helper with the same numbers; left alone to keep a long-stable
  load path untouched. Its 1.6 s window may be short for the SMB sharing-violation EBUSY ("fine seconds later").
- No MRC-staging retry helper existed to reuse (`source_staging` has none); the vikingvolume/container_storage
  retries are for XML writes.
- Build2: the EBUSY stopped after James restarted backup1's SMB service; the retry is still wanted.
- Tests: `nornir-imageregistration/tests/test_io_retry.py` (helper; `load_raw_tile` and the histogram read survive
  injected EBUSY; persistent EBUSY still fails).

## 3. Histogram step uses ~2 cores (Build2: RC2 1226, 1270 tiles, ~5 min on 128 cores)

`image_stats.Histogram` already submits one task per tile to the global **thread** pool, but per-tile work is
GIL-bound. Measured on 16 synthetic 4080x4080 uint16 TIFs (this workstation, local SSD):
- serial: open + `convert("I")` 0.42 s, `HistogramOfArray` (stride 4, 2048 bins) 0.06 s per tile;
- threads 1 / 4 / 16: 7.3 / 4.0 / 2.0-3.5 s for 16 tiles: at most ~2-3.5x, so ~2 cores busy, matching Build2.
- Decoding natively (`np.asarray(im)` for mode `I;16`, no `convert("I")`) is 0.16 s per tile and gives identical
  values and an identical histogram; serial 3.25 s for 16 tiles, but threads still scale poorly (2.3-2.7 s).
Proposal (not made):
1. Small and safe: in `__HistogramFileSciPy__`, skip `convert("I")` for integer modes (`I;16`, `I;16B`, `I`, `L`):
   ~2x less CPU per tile, identical histogram (verify with the existing histogram tests plus a mode matrix).
2. Real scaling: run the per-tile histogram in a process pool (`GetGlobalMultithreadingPool`) with bounded
   in-flight tasks, returning only the 2048-bin histogram per tile. Larger change; needs a timing run on Build2.

## Test results (2026-11-05, venv pyre314, NumPy backend)
- New tests: 12 passed.
- `nornir-buildmanager/tests/importers` (minus `test_dm4_filename_metadata.py`, which cannot import `dm4` in this
  venv), `test_noise_crush.py`, `test_ImageStats.py`, `test_crushed_assembly.py`, `test_mdoc_mrc2tif.py`,
  `test_mrc_histogram_in_flight_bound.py` with `-m "not graphical and not slow and not gpu and not needs_data"`:
  264 passed, 1 skipped, 1 failed: `test_recover_notes.py::...test_notes_text_round_trips_to_file_and_xml`, the
  known Hypothesis flake listed in nornir-verify-change (fails identically on HEAD).
