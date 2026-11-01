# Translate: automatic recovery of misplaced blocks (set aside 2026-11-01)

Part 3 of the translate robustness plan (1: report and join check, 2: manual offsets, 3: automatic
recovery, 4: Pyre mosaic editor). 1 and 2 are on `dev` (nornir-imageregistration 7569064 and later,
nornir-buildmanager 0c5873c). 3 was built, tested on real data, and **not committed**: it did not
meet the bar for moving tiles without a person looking. The code is kept here as patches:

- `translate-block-recovery-imageregistration.patch`: `nornir_imageregistration/translate_recovery.py`,
  `tests/test_translate_recovery.py` (9 tests), the hook in `MosaicTileset.ArrangeTilesWithTranslate`
  (env `NORNIR_TRANSLATE_RECOVER_BLOCKS`), and `TranslateReport.recovery_attempts`. Applies to
  nornir-imageregistration 8685a4b (`git apply`); 27 tests pass there with it applied.
- `translate-block-recovery-buildmanager.patch`: logging of attempts and a `BlocksRecovered` attribute
  in `operations/registration.py`, with a test.

## What it does

For each secondary block (a matched group of >= 10 tiles other than the main one, from
`TranslateReport.check_joins`): assemble the tiles of both blocks near their seam at ~32 full-res
px/pixel, score every shift within 3 tile widths by masked NCC (Padfield 2012) over the overlap,
pick the shift with the highest Fisher z among shifts whose NCC clears a bar, refine the position
at 8 px/pixel, move the block, translate again, and keep the result only if the two blocks then
form one matched group and the section median NCC did not fall.

## Evidence

Estimator alone, on RC3 0800's good translated layout with a block displaced (tiles at
downsample 4): 86-427 tiles moved by 3,000-6,000 px came back within 16 px, block NCC 0.69-0.83.

Full pipeline (translate from stage positions with a displaced block, then recovery), RC3 0800:

| run | displaced | outcome |
|-----|-----------|---------|
| a | 30% by (5000, -1500) | accepted; moved tiles 44 px from reference (noise 7 px) |
| b-d | same | estimate right each time, rejected: raw-z ranking bug (b), gate too strict (c, d) |
| e | same | accepted; moved tiles 21 px from reference, final main block 845 of 853 |
| f | 20% by (-3000, 4000) | **missed**: true shift scored NCC 0.25 (translate had bent the block, 142 px internal spread); best z went to a 46-tile overlap at NCC 0.10 |

Real flagged sections (RC3 non-stos list, 81 screened at downsample 32; 60 hold together):

| section | outcome |
|---------|---------|
| 0633 | 25-tile block moved 12,000 px and accepted (829/832 joined), but the moved tiles sit around a blank resin hole; the assembled image there looks worse than 2022. Smooth gradients over blank regions give high NCC whatever the alignment, so the acceptance test can be fooled. |
| 1655 | 101-tile block joined (main 299 -> 405); not inspected by eye |
| 1337, 1506, 1637 | nothing moved (no confident shift, or rerun did not join) |
| 0590 | current translate already holds together; recovery not run |

## Why set aside

- It works when the misplaced block keeps a clean seam, and misses when translate has bent the
  block, which is the usual real case (run f).
- Its acceptance test (the block joins the main group after a rerun) can pass in low-texture
  regions (0633). A wrong automatic move silently corrupts a layout; a flagged section does not.
- Three rounds of retuning the ranking and gates each fixed the previous case and met a new one.

## If picked up again

- Use the estimator as a suggestion in the Pyre mosaic editor (part 4): a person confirms, and the
  result is saved as a manual offset.
- Score overlaps with a texture measure that ignores smooth gradients (high-pass before NCC, or
  require a minimum local variance) before trusting a join in blank regions.
- Estimate from translate's pair offsets rather than assembled canvases, so a bent block is
  handled tile by tile.
