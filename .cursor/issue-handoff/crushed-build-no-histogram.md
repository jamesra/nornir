# Crushed builds: no histogram pass, no contrast on crushed filters, TEMBuildCrushed.sh (2026-11-05)

Requested by James via Build2: Host while importing RC2 raw sections crushed. James: "We don't need a histogram
for crush builds ... we are not building leveled images when building crushed mosaics", "NO contrast mapping may
be applied to crushed filters anywhere downstream", and (RC2 139) the crush offset of signed sources must follow
the data minimum. Approved to commit and push.

## What changed (nornir-buildmanager, nornir-imageregistration)

1. **ImportIDoc, crushed path: no histogram pre-pass.** The noise sample (16 tiles) sets step, offset and bits;
   `GetSectionContrastSettings` / `CalculateHistogram` / `PlotHistogram` / `TryAddHistogram` run only on the legacy
   path (-NoCrush, 8-bit sources, or an existing uncrushed filter kept). The legacy path is the same code in the same
   order (the histogram now runs after the crush decision instead of before it; its inputs and outputs are unchanged).
2. **Code histogram during conversion.** `noise_crush.crush_tile_to_file` returns `CrushTileStats` (code histogram,
   pixels clipped high/low); `shared.CrushTiles` sums them and returns `CrushSectionStats`, logging any clipping
   (that would mean the sample under-estimated the range; the depth comes from the sample now, not a full histogram).
3. **No contrast values on crushed filters.** Crushed filters no longer get `MinIntensityCutoff`, `MaxIntensityCutoff`
   or `Gamma`; existing ones are removed on re-import (`shared.ClearCrushedFilterContrast`). Prune still needs the
   section's span in code units to keep its score scale, so the filter gets `CrushCodeSpan`: from the converted tiles'
   code histogram at the import's cutoff fractions (IDoc), from the histogram cutoffs (MRC, which keeps its histogram
   pass for now), or moved over from the old cutoffs of filters imported before this change (RC1_Crush keeps its
   Prune scale). `PruneObj.CrushedScoreScale` reads `CrushCodeSpan` first, then the old cutoffs.
4. **Consumer guards** (`tile.IsCrushedFilter`, marker = the Crush* attributes incl. `CrushVersion`):
   `HistogramFilter` (Histogram pipeline) and `AutolevelTiles` (AdjustContrast) skip crushed filters with a log line;
   `setters.SetContrastRange` (SetContrast) refuses them.
5. **Signed sources (RC2 139 bug).** `SectionNoise.sample_low` = the 1e-4 quantile of the sampled pixels for signed
   dtypes; `SectionCrushParams` uses it as `section_min`, so one stray negative pixel no longer sets the offset.
   139 (int32 TIFs, DataMode 1): a -15951 pixel gave CrushOffset -15951 and 9-bit codes (Raw16); now offset 0 and 8 bits.
   uint16 results are unchanged (offset is always 0 there). Signed noise caches written before `sample_low` existed are
   re-estimated, so a re-import of a signed section (RC1 MRC if signed) may get a different offset and re-crush.
6. `scripts/TEMBuildCrushed.sh` (below).

## TEMBuild.sh stages vs TEMBuildCrushed.sh

| TEMBuild.sh stage | TEMBuildCrushed.sh | Why |
|---|---|---|
| (import, separate script) ImportIDoc | unchanged, no -CameraBpp | -CameraBpp is ignored with a warning when crushing |
| Prune -InputFilter Raw8 -Downsample 4 -DefaultThreshold 10.0 | kept | crushed scores are rescaled to the contrast-stretched 8-bit scale (`CrushCodeSpan`), so the threshold keeps its meaning |
| Histogram -Filters Raw8 | **dropped** | only feeds AdjustContrast; skips crushed filters |
| AdjustContrast -InputFilter Raw8 -OutputFilter Leveled | **dropped** | would contrast-map crushed codes into Leveled; skips crushed filters |
| Mosaic -InputFilter Leveled | **changed**: -InputFilter Raw8 | translate/refine use NCC, insensitive to the code scale |
| Assemble -Filters Leveled -Downsample 8,16,32 | **changed**: -Filters Raw8 | crushed assemblies keep the codes (tile_value_scale = max code) |
| MosaicReport -AssembleFilter Leveled | **changed**: -AssembleFilter Raw8 | no Leveled filter; -ContrastFilter Raw8 just reports no contrast |
| CreateVikingXML | kept | see the Viking display note below |

Not run end to end: no crushed test volume on this workstation. Raw8 pyramid levels 4/8/16/32 are generated on demand
(`GetOrCreateLevel(GenerateData=True)`), as Leveled levels were.

## Audit: who reads contrast from a filter, and did it apply it to crushed codes?

| Consumer | Applied contrast to crushed codes before? | Now |
|---|---|---|
| ImportIDoc / ImportMRC filter attributes | wrote Min/Max/Gamma (code units) as hints; IDoc also built the histogram plot | not written; old ones removed (span kept as `CrushCodeSpan`) |
| HistogramFilter (Histogram pipeline) | would histogram crushed codes for AdjustContrast | skips crushed filters |
| AutolevelTiles (AdjustContrast) -> Leveled | **yes**, if run on a crushed Raw8 | skips crushed filters |
| SetContrastRange (SetContrast) | would set an AutoLevel hint on a crushed filter | refuses |
| PruneObj.CrushedScoreScale | used the cutoffs to scale scores (no pixels changed) | uses `CrushCodeSpan`, falls back to old cutoffs |
| Assemble (AssembleTransform, Mask) | no: loads with tile_value_scale = max code, writes codes + crush chunk | unchanged |
| BuildTilePyramids / Shrink | no: codes averaged, crush chunk carried | unchanged |
| **AssembleTilesetNumpy (AssembleTiles, 512 px optimized tiles)** | **yes, implicitly**: tiles loaded without tile_value_scale, so each tile is divided by its own maximum, and saved as stretched 8-bit | **not fixed here**: another session is working on this function tonight (1240 optimized tiles). Fix: pass `tile_value_scale=crush.max_code` to `CreateFromMosaic` and save codes with `codes_from_unit_image` + the crush chunk, as Assemble does |
| Mosaic translate / grid refine (registration.py) | per-tile max normalisation in memory only, no output; NCC is scale-invariant | unchanged; passing tile_value_scale would make it consistent |
| CreateBlobFilter (channel.py) | assembled crushed image loaded with per-image max scaling, Blob output 8-bit | not changed (derived filter for brute alignment only); could take value_scale from the crush chunk |
| CreateVikingXML / Viking | no contrast read in nornir | Viking will show raw codes (dark, ~40-50 levels): display mapping belongs in the viewer |
| diagnostics.PrintContrastValues, reporting (MosaicReport), setters.PrintContrast | print only | print nothing for crushed filters |
| ChannelNode.RemoveFilterOnContrastMismatch / ContrastHandler | legacy branch only | unchanged |

## Answers

- **What Prune scores today:** Raw8 at ds4. `TEMBuild.sh` passes `-InputFilter Raw8 -Downsample 4 -DefaultThreshold 10.0`,
  and the Prune pipeline's own default -InputFilter is Raw8 too. RC2's prunes were Raw8 at ds4 as well.
  Note: today's Prune scores are about 217x the 2015 scores, so `-DefaultThreshold 10.0` keeps nearly every tile.
  The RC2 rescue used 2200 (the old 10 is about 2169 on today's scale). That needs fixing in both scripts.
- **Prune on crushed codes:** works. The score is a sum of per-region standard deviations, rescaled by 255 / span, so
  it lands on the legacy 8-bit scale. Fixed intensity constants elsewhere in Prune: none found.
  The rescue skill's flat-tile rule (std < 8 on Leveled ds16) has no Leveled to read in a crushed build. Its crushed
  equivalent is std < 8 * span / 255 codes on Raw8 ds16.
- **Translate (Mosaic) and grid refine on crushed codes:**
  - Both use masked NCC, which is invariant to scale and offset. Each tile is divided by its own maximum, which does
    not matter for NCC.
  - Extrema masking masks connected regions at exactly the tile's min or max value larger than the size cutoff.
    With ~40-50 code levels the top code covers more pixels than in a stretched tile, but noise pixels at one value
    rarely connect into regions over the cutoff, and ds4/ds16 averaging adds levels back.
  - Expected to work, but not verified on a real crushed section. First check: compare a crushed RC2 section's
    Translated layout with its legacy one.
  - No fixed intensity thresholds in translate or refine (feature_score_threshold is off by default).
- **Histogram step cost (Build2):** gone from crushed IDoc imports. MRC still histograms the whole file (needed today
  for the span and the bit depth there); moving MRC to the noise sample plus conversion-time stats is the next step.

## Tests (2026-11-05, venv pyre314, NumPy)
- New: `nornir-buildmanager/tests/importers/test_crushed_no_contrast.py`:
  - int32 outlier offset, before and after;
  - genuinely negative signed data;
  - uint16 unchanged;
  - old signed caches re-estimated;
  - tile and section stats, code span;
  - cutoffs moved into the span;
  - Prune scale;
  - AdjustContrast, Histogram and SetContrast skipping or refusing crushed filters.
- `test_crush_import.py`: its fake pool task gained `wait_return`.
- Suite results are in the commit summary.

## Consistency with `.cursor/plans/crush_optimized_pipeline.plan.md` (D1-D6, 2026-11-01)

- Marked partly done there: `stages` (Leveled never produced for crushed filters; Histogram/AdjustContrast/SetContrast
  skip or refuse them; Prune reads codes on purpose) and `scripts` (TEMBuildCrushed.sh, with
  `NORNIR_CRUSHED_FILTER` picking Raw8 or Raw16). TEMAlign, the .cmd scripts and Pipelines.xml defaults are still open.
- **One tension for James:** the plan keeps the section contrast hints for display (Viking window/level in counts,
  exports and thumbnails leveled in memory, plan sections 4-5 and D5). Today's instruction removes them from crushed
  filters. What remains is `CrushCodeSpan` (for Prune) and the code histogram, which is computed during conversion but
  not stored. When the Viking/export work starts, store display-only hints under names no nornir stage reads (e.g.
  `CrushDisplayMin/Max` from the conversion-time code histogram) rather than restoring `Min/MaxIntensityCutoff`.
- The plan's loader/inflate (D1, D4), save/re-crush (D2), pyramids, blob retune and brightness-drift todos are untouched.
