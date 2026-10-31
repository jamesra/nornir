---
name: Noise-crushed import
overview: "ImportIDoc/ImportMRC store raw >8-bit TEM tiles as section-wide noise-step codes (step = 2.5 x Haar-MAD sigma) in Raw8 PNGs, opt-out with -NoCrush. ~86% smaller than raw uint16; parameters on the filter and in each PNG."
todos:
  - id: core-module
    content: nornir_imageregistration/noise_crush.py (sigma, params, crush/uncrush, PNG tEXt, per-tile worker) + tests/test_noise_crush.py
    status: completed
  - id: importer-plumbing
    content: importers/shared.py (noise cache, SectionCrushParams, ResolveCrushMode, CrushTiles), idoc/mrc/mdoc wiring, -NoCrush/-CrushK in Pipelines.xml
    status: completed
  - id: prune-scale
    content: Prune scores of crushed tiles scaled by 255/(qmax-qmin) (PruneObj.CrushedScoreScale)
    status: completed
  - id: unit-tests
    content: tests/importers/test_crush_import.py
    status: completed
  - id: data-tests
    content: RC2_Micro/17 IDOC pipeline (import -> Assemble) with crushing on; SmallMouse MRC crushed import vs 2014 build
    status: in_progress
  - id: docs
    content: docs/guides/tem_scripts.rst section; docs/publication_notes.md entries
    status: completed
  - id: visual-check
    content: User check of Leveled/Assemble/Viking views for banding (10-17 codes span the tissue)
    status: pending
  - id: anscombe-followup
    content: "Follow-up: variance-stabilised crush in electron units (gain from CountsPerElectron when the idoc has it, else a per-section photon-transfer fit); record gain/read noise per section"
    status: pending
isProject: false
---

# Noise-crushed import

Design, measurements and rejected options: `docs/publication_notes.md` (2026-10-30 entries). Working plan with the
full reasoning: `~/.claude/plans/nornir-noise-crush-importer.md`.

## Decisions (user, 2026-10-30)

- `k = 2.5` true sigma (the September "3 sigma" was ~6 sigma; Haar HH lacked the 1/2 factor).
- One step per section (median of up to 16 sampled tiles' sigma), cached as `Histogram.noise.json` beside the
  histogram cache.
- PNG level 6 with a `nornir_crush` tEXt chunk; filter `Raw8` (`Raw16` only if codes need more than 8 bits) with
  `Crush*` attributes.
- No contrast stretch; contrast cutoffs become hints in code units.
- Existing uncrushed filters are kept (re-imports never rebuild old sections); a crush-parameter change or `-NoCrush`
  on a crushed filter cleans and rebuilds it; locked filters keep what they hold.
- Gain / counts-per-electron is deferred to the Anscombe follow-up. RPC3 (OneView) idocs record
  `CountsPerElectron = 115.93`, but measured pixel noise is ~10x below that Poisson prediction (scintillator spread),
  so the step stays on measured sigma.
