---
name: Crush-optimized pipeline
overview: "Crushed tiles stay crushed end to end. The image loader sees the nornir_crush PNG chunk and inflates to 16-bit counts; every derived image (pyramid level, assembled section, volume tile) is re-crushed with the same section quanta; crushed filters are never leveled, and contrast moves to display time (Viking) and to in-memory normalization where an algorithm needs it."
todos:
  - id: decisions
    content: "James: D1-D6 decided 2026-11-01 (blob retuned; thumbnails pre-leveled, downloads inflated server-side; ships all at once). Open: per-tile brightness gain (beam drift) as a separate step"
    status: completed
  - id: blob-retune
    content: "Retune the blob metric for inflated counts; compare on crushed and uncrushed sections"
    status: pending
  - id: brightness-drift
    content: "Measure per-tile brightness drift across overlaps on RC3; if material, per-tile gain from overlap least squares, stored as metadata, applied on inflate/assemble"
    status: pending
  - id: loader
    content: "nornir_imageregistration: one crush check in the loader (LoadImage / _load_image_by_extension_once); inflate to uint16 counts; route the raw Pillow readers through it or make them crush-aware"
    status: pending
  - id: save
    content: "SaveImage(crush_params=...) re-crushes and writes the chunk; derived ImageSets/TilePyramids record the filter's Crush* attributes"
    status: pending
  - id: pyramids
    content: "Shrink/BuildTilePyramids and the Viking tile pyramid keep crushed codes and the chunk (average codes, round, copy chunk)"
    status: pending
  - id: stages
    content: "Mosaic, Assemble, Blob, Stos, MosaicToVolume, prune and histogram on the crushed filter; Leveled not produced for crushed filters"
    status: pending
  - id: scripts
    content: "TEMBuild/TEMAlign (.sh/.cmd) and Pipelines.xml defaults pick the crushed filter (Raw8 or Raw16) instead of Leveled"
    status: pending
  - id: exports
    content: "MosaicReport, ExportImages, ExportTrainingData level in memory from the contrast hints (they produce pictures, not pipeline data)"
    status: pending
  - id: viking
    content: "Viking dev and VikingLegacy: decode 16-bit + tEXt, per-section crush params, window/level in TileLayout.fx, R8/R16 by CrushBits; HDR output optional"
    status: pending
  - id: validation
    content: "RC2_Micro/IDOC and one RC3 section end to end, crushed vs leveled: translate/refine seam metrics, stos parity, blob output, Viking visual"
    status: pending
isProject: false
---

# Crush-optimized pipeline

Follows [noise_crush_import.plan.md](noise_crush_import.plan.md), which crushes at import only: today the crushed
`Raw8`/`Raw16` filter is leveled by `AdjustContrast` into an ordinary 8-bit `Leveled` filter, and everything after
that (pyramids, mosaics, assembly, alignment, Viking) uses `Leveled`. Nothing after import reads the `nornir_crush`
chunk. This plan makes crushed data flow through the whole pipeline.

## Direction (James, 2026-11-01)

- The crush check lives in the **image loader**: a PNG with the `nornir_crush` chunk is inflated to 16 bpp
  (counts ~= q x step + step/2 + offset).
- When assembled images are saved they are **re-crushed with the same quanta** (the section's step and offset).
- **Crushed images are not leveled.** Contrast is applied at display time.
- Viking reads the chunk (or the volume's crush metadata) and maps codes to the screen with window/level.

## Where pixels are read and written today

Survey 2026-11-01 (file:line in the session notes; summary here). Paths: `nir` = `nornir_imageregistration`,
`nbm` = `nornir_buildmanager`.

**Readers.** One NumPy entry point: `nir/core/_core.py` `_load_image_by_extension_once` (via `LoadImage`,
`_LoadImageByExtension`), Pillow. With a float dtype it divides by **each image's own max**, so tiles are stretched
individually; `ImageParamToImageArray` on an ndarray divides by the dtype max instead (inconsistent today). Callers:
`Tile.Image` (translate, refine, assemble), `arrange_mosaic`, `local_distortion_correction`, StosBrute
(`image_permutation_helper`), `TransformStos`, `stos_quality`, `ImageStats.Create`.
Readers that **bypass** it (and would miss the inflate): `pillow_helpers.load_image_array` (Viking tile pyramid
`tileset_functions.py:322`, pyramid align `tile.py:2437`, segmentation export), `blob_filter._load_legacy_tile_image`,
the SciPy histogram reader (`image_stats.py:628`), and `Shrink` (Pillow resize + save, never decoded to NumPy; used
by `BuildTilePyramids`, `BuildImagePyramid`).

**Writers.** `SaveImage` (Pillow, no text chunk; `bpp=8` divides ints above 255 by the image's own max) for contrast
output, pyramid tiles, assembled sections (`tile.py:1453`, filter `BitsPerPixel`), Level-1 volume tiles
(`tile.py:1845`), blob (bpp 8, 0-255), stos outputs. `Shrink` and the Viking pyramid (`tileset_functions.py:390`)
save with Pillow and drop the chunk. Only `save_crushed_png` writes it.

**ImageMagick** (bypasses any Python hook): `identify` for `GetImageBpp`/stats (used to choose `InputBpp`),
`BuildImagePyramid` `convert -interlace`, `AssembleTilesetFromImageSet` `convert -depth 8` (live), `TilesFromImage
-depth 8`, legacy correction `convert`s. Whether `convert` keeps tEXt is unverified; `-depth 8` would destroy 16-bit
codes regardless.

**8-bit assumptions.** `image_to_uint8`, blob `_OUTPUT_MAX=255` and its metric `(median+1)/(var+1)` tuned on
0-255 stretched input, `CrushedScoreScale` (assumes code units), `CutoffValuesForHistogram(Bpp=8)` /
`AutolevelTiles` `or 8`, histogram bin defaults (256 / max 255), `_imagemagick_gray_fraction` (8), segmentation
export `_as_uint8_gray` and 0/255 blank tests, `vikingvolume.py:903` (`bits=8`). `CreateExtremaMask` already uses
per-image min/max and is scale-free.

**Consumers of `Leveled`.** Pipelines.xml defaults: AdjustContrast output, CreateBlobFilter input,
ExportTrainingData. Scripts: `TEMBuild(.sh/-import.sh/.cmd)` Mosaic / Assemble 8,16,32 / MosaicReport;
`TEMAlign(.sh/.cmd)` Blob input, RefineSectionAlignment `-Filter`, Assemble ChannelToVolume, MosaicReport,
ExportImages. The scripts also hard-code `Raw8`, which is `Raw16` when codes need more than 8 bits
(`importers/shared.py:893`).

## Design

### 1. Loader (one check)

- In `_load_image_by_extension_once`: after Pillow opens a PNG, read `im.text.get('nornir_crush')`. `save_crushed_png`
  writes the chunk before IDAT, so Pillow has it at open without decoding pixels: the check costs a dict lookup.
- If present: decode codes, inflate with `noise_crush.uncrush` to **uint16 counts** (dtype=None), or to the
  requested float dtype under the normalization chosen in decision D1.
- `LoadImage(..., inflate=True)` by default (D4); `inflate=False` returns the codes for assembly and registration.
- Expose the parameters to callers that will save derived images: `LoadImage(..., return_crush=True)` or a sibling
  `LoadImageWithCrush(path) -> (image, CrushParams | None)`; `read_crush_params(path)` stays for metadata-only use.
- Route the bypassing readers through the loader, or make them crush-aware where they deliberately work on codes
  (pyramids, see 3; histograms, see 5).
- CuPy: upload the 8-bit codes and inflate on the device (half the transfer of uint16 counts).
- Unify the float normalization of path and ndarray inputs while here (today: per-image max vs dtype max).

### 2. Save (re-crush with the same quanta)

- `SaveImage(path, image, ..., crush_params=None)`: when given, `crush(image, params)` then `save_crushed_png`.
  Values outside `[offset, offset + max_code x step]` clip, as at import.
- The quanta come from the section, not the image: the source filter's `Crush*` attributes (or the tiles' chunk). Every
  derived node (TilePyramid levels, assembled ImageSets, Level-1 volume tiles, downsampled assemblies) records the
  same `Crush*` attributes so a stage can find them without opening a PNG.
- Never send crushed data through ImageMagick: replace `convert -depth 8` (`AssembleTilesetFromImageSet`) and the
  interlace pass with Pillow for crushed filters (or everywhere), and use the chunk/attributes instead of `identify`
  to learn the bit depth.

### 3. Pyramids and downsampling

- Inflate, average, re-crush with the same quanta, copy the chunk (D2). Because a code inflates to the middle of its
  step, this equals rounding the averaged codes to the nearest code; `Shrink` must not truncate codes directly.
- Averaging lowers noise, so lower levels could afford a finer step; the rule is the same quanta at every level
  (one set of display parameters per section).

### 4. Stages

| Stage | Today | Crush-optimized |
|-------|-------|-----------------|
| Import | writes crushed `Raw8`/`Raw16` + chunk | unchanged |
| Prune | scores raw codes; `CrushedScoreScale` = 255/(max-min) in code units | scores on inflated counts; scale becomes 255/((max-min) x step), or prune reads codes on purpose |
| Histogram / AutoLevel | histogram of codes; cutoffs become hints in code units | histogram kept for the display hints only; no Leveled output for crushed filters |
| Mosaic translate / refine | `Leveled` | crushed filter through the loader; float normalization per D1 |
| Assemble (section) | `Leveled` tiles, saved at filter bpp | inflate, transform and blend in counts, re-crush on save |
| Mask | from assembly coverage | unchanged |
| Blob | `Leveled` assembled image, metric tuned on 0-255 | per D4: level in memory from the hints, or retune |
| StosBrute / stos refine / SliceToVolume | blob + `Leveled` assemblies | blob as today; refine on crushed assemblies via the loader |
| MosaicToVolume / volume tiles | `Leveled` | crushed, re-crushed per section on save |
| MosaicReport / ExportImages / ExportTrainingData | `Leveled` | level in memory from the hints (pictures, not data), D5 |

### 5. Viking (both clients: `D:\src\git\Viking` dev, `D:\src\git\VikingLegacy` Legacy)

Survey 2026-11-01: both decode tiles with System.Drawing keeping only the first byte per pixel
(`TextureReaderV2.cs`), read no PNG metadata, have no window/level in `TileLayout.fx`, and render to an 8-bit back
buffer (HDR is detected only to rebuild the swap chain). An 8-bit crushed tile would display raw codes (dark, flat);
a 16-bit one would display noise.

- Decode with a library that reads L16 and tEXt (ImageSharp is already referenced by WebAnnotation).
- Crush parameters per section from the volume XML (preferred: one read per section) with the tile chunk as fallback.
- Texture format by section (D3): 8-bit for uncrushed sections, 16-bit (R16) of inflated counts for crushed ones.
- Window/level in the shader: `out = ((x - min) / (max - min))^gamma`, with min/max/gamma in counts from the
  section's contrast hints; live adjustment becomes possible.
- The local tile cache stores the crushed PNGs; inflation happens at texture upload.
- HDR is an output choice (10-bit or FP16 swap chain), useful for narrow windows or 16-bit codes; with ~35-40 codes
  per RC section an 8-bit output already has more levels than the data.
- VikingXML / volume export must carry the crush parameters and contrast hints per section.

## Decisions (James, 2026-11-01) and what remains open

- **D1 Float normalization: section constant (decided).** Quanta are per section (one step, offset and bits for
  every tile of a section, set at import), so an inflated tile requested as float is divided by the section constant
  `offset + max_code x step`. Every tile of a section shares one scale (today each tile is stretched by its own max).
- **D2 Rounding: none special (decided).** Downsampling averages codes and assembly interpolates them, giving
  fractional codes. Inflate, average/blend, and re-crush with the same quanta: since a code inflates to the middle of
  its step, re-crushing the average lands on the nearest code. Same quanta at every level.
- **D3 Both crushed and uncrushed volumes (decided).** Uncrushed sections: 8-bit textures in Viking, `Leveled` as
  today. Crushed sections: 16-bit textures of inflated counts, window/level in counts. Quanta (`Crush*`) are stored
  per section in the volume metadata so images can be sent and inflated anywhere; local file caches (Viking's
  included) keep the crushed PNGs.
- **D4 Loader inflates by default (decided), with `inflate=False`** for operations that work on codes directly
  (assembly, registration): uncrush is affine, so they need not inflate, and saving re-crushes as in D2.
  Blob's metric `(median+1)/(var+1)` was tuned on `Leveled` 0-255 input; inflated counts (~0-16,000, a different
  contrast) are not that input. **Decided: retune blob**, and test the retuned metric on uncrushed data too (it may
  do as well or better there).
- **D5 Pictures (decided).** The volume summary page uses small pre-leveled 8-bit thumbnails. Full-image downloads
  for browser users are inflated (and leveled) on the server, since a browser `<img>` cannot read PNG text chunks.
- **D6 Viewers and rollout (decided).** Viking and the volume summary page are the only viewers of a volume. We control
  Viking's release, so the feature ships all at once (nornir, both Viking clients, summary page); no interim
  `Leveled` for crushed volumes.

## Beam brightness drift (James's question, 2026-11-01)

Beam brightness can drift during a section's capture, giving visible brightness steps between tiles. Dividing each
tile by its own quanta at import would correct this only partly: the step is k x the tile's noise sigma, and when the
beam brightens by a factor a the signal scales by a but the noise by ~sqrt(a) (shot-noise limited) or ~1 (read-noise
limited), so per-tile codes scale by between sqrt(a) and a, removing at best about half of the change in log terms.
Measured noise on these detectors is not Poisson-like either (RPC3: ~10x below the Poisson prediction, scintillator
spread). It would also break the per-section quanta (D1), leave assembled images without a single quanta to re-crush
with, and fold an adjustable intensity correction into an invertible storage encoding.

Proposed instead (not decided): keep per-section quanta for storage, and correct brightness as its own step. After
translate, overlapping tiles should agree in the overlap; solve once per section for a gain (and optionally an
offset) per tile by least squares over all overlaps (the join check already scores them), store the gains as
per-tile metadata, and apply them on inflate/assemble. Reversible, complete rather than partial, and it also works on
uncrushed data. First step: measure the drift (per-tile brightness ratios across overlaps) on a few RC3 sections to
size the problem.

## Validation

- Unit: loader inflate (8- and 16-bit codes, offset for signed data), save round trip (same quanta, chunk present),
  pyramid on codes vs on counts (difference <= 1 code), assemble re-crush clip behaviour.
- Pipeline: RC2_Micro/17 IDOC (import to Assemble) crushed vs current leveled path; one RC3 section through Mosaic
  and Assemble: translate/refine seam metrics within the usual noise, stos parity on a section pair, blob output
  comparison.
- Size and speed: tile, pyramid and assembled image bytes, crushed vs Leveled; loader cost.
- Viking: both clients on a crushed and an uncrushed section, normal and HDR monitor.
