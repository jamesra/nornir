# Chunk 13 — registration (`stos_brute`, phase correlation, `arrange_mosaic`)

## Findings

- Serial and batched phase correlation are an intentional pair. `refine_shared/cell_measurement.py` already wraps `batched_find_offset` for the shared measurement. Do not collapse the two implementations in this review; the serial/batched rule requires them to stay aligned and verified.
- `stos_brute` and `arrange_mosaic` are registration algorithms. They belong here. Buildmanager `registration.py` orchestrates nodes and calls into this package. That direction is correct.
- No SAM2 or crop-mask function duplicates a phase-correlation peak.

## Carry forward

Leave serial/batched mirrors alone.
