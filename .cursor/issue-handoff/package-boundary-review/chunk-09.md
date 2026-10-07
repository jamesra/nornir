# Chunk 9 — buildmanager importers

## Findings

- `importers/mrc.py` opens images with Pillow while converting microscope files into a volume. The conversion policy (which page, which dtype, which axis) is the importer’s job. The byte decode of a standard image file is imageregistration’s job, once a raw loader exists that does not run `LoadImage`’s mask-and-noise path.
- Do not change importer output in this review. Any later switch needs a before/after pixel compare on a real small section (`TESTINPUTPATH`), not a unit fixture alone.

## Carry forward

Importers stay proposal-only.
