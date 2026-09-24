# RC2 Grid16 refine fixtures (Manual Leveled)

Imported into `D:/nornir-testdata/refine_fixtures/RC2/Grid16/` from
`Y:/Volumes/RC2/TEM/Grid16` (**Leveled only**, no Blob).

## Semantics

A/B later runs `RefineStosFile` on **Automatic input**, then scores against **Manual gold**.

Do **not** use the Grid16 group-root stos as `input.stos`. For Manual pairs the pipeline
usually copies Manual over the group-root and **deletes** `Grid16/Automatic/`. That
group-root is already gold, not the pre-refine Automatic product.

| File | Meaning |
|------|---------|
| `input.stos` | Automatic **input** (what refine would have seen) |
| `gold.stos` | Unsuffixed Manual Leveled (what is reasonably good) |
| `control.png` / `mapped.png` | Grid16 Leveled images for the pair |

### How Automatic input was obtained

1. **`Grid16/Automatic/<pair>_…Leveled.stos`** when it still exists.
2. Otherwise reconstruct: load **Grid32** group-root (ds32 Mesh/Grid product),
   `ChangeTransformPixelSpacing(oldspacing=32, newspacing=16)`, and rewrite image
   paths to Grid16 Leveled. That is the scaled previous-group product the Grid16
   Automatic pass would have started from.

Manual variants (`-Rigid`, `-Mesh`) were **not** used as gold.

Catalog: `D:/nornir-testdata/refine_fixtures/catalog.sqlite`

## Pairs (unique unsuffixed Manual Leveled)

| Pair | Confirmed tags | Automatic input source |
|------|----------------|------------------------|
| 39-41 | | Grid32 scaled 32→16 |
| 41-42 | | Grid32 scaled 32→16 |
| 66-67 | | Grid32 scaled 32→16 |
| 240-241 | coherent-residual | Grid32 scaled 32→16 |
| 784-782 | | Grid32 scaled 32→16 |
| 785-784 | | Grid32 scaled 32→16 |
| 825-822 | | Grid32 scaled 32→16 |
| 897-896 | | Grid32 scaled 32→16 |
| 945-943 | | Grid32 scaled 32→16 |
| 1215-1214 | drying-front | `Grid16/Automatic/` (surviving 10×10 mesh) |

Strain-crop `bbox_yxhw` on several pairs is near full FOV; `certified_ids` is empty.
Scoring vs gold still uses the full `gold.stos`; certified-cell metrics will be absent
until cells are marked.

## A/B

`nornir-ab-refine-fixtures` reads each fixture’s `input.stos` and writes baseline vs
`NORNIR_REFINE_TRUSTED_MESH` outputs. Do not run that against the live volume; the
fixtures already contain the Automatic input copies.
