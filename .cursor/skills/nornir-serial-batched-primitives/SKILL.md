---
name: nornir-serial-batched-primitives
description: >-
  Phase correlation and serial+batched registration math: grep callers, keep
  serial/batched mirrors aligned, run the verification matrix, final perf on
  ≥100-tile sections. Use when editing phasecorrelation, batched_phase_correlation,
  stos_brute, arrange_mosaic, local_distortion_correction, or related scripts/tests.
---

# Serial + batched primitives

Paired rule: [`.cursor/rules/Serial-batched-primitives.mdc`](../../rules/Serial-batched-primitives.mdc).

## Before merge

1. **Grep callers** of any changed primitive (serial and batched entry points).
2. **Keep serial/batched mirrors aligned** — same gates, tolerances, and semantics unless an intentional divergence is documented in this skill.
3. **Run the verification matrix** below for affected pathways.
4. **Final performance sign-off** must use a **real section with ≥100 tiles** (default: RPC3 0195 per `.vscode/launch.json`), with downsample and refine parameters matching launch configs — **not** the grid refine input section fixture (4 tiles).

## Script / test inventory

Maintain these tables in the **same commit** when adding, removing, or renaming a script or pytest module that benchmarks, profiles, compares, verifies, or gates phase correlation / serial+batched registration behavior.

### Scripts (by pathway)

| Pathway | Scripts (update as inventory changes) |
|---------|----------------------------------------|
| Phase correlation | `nornir-imageregistration/scripts/microbench*.py`, `compare*.py`, `verify*.py`, `audit*.py` (incl. opt-in `audit_cupy_item_bench.py`), `tabulate*.py`, `run_*investigation*.sh` |
| STOS / refine | Scripts and launch configs that exercise `stos_brute` / refine under `nornir-imageregistration/scripts/`; `python -m nornir_imageregistration.stos_registration_debug` |
| Mosaic arrange | Scripts touching `arrange_mosaic` |

### Pytest modules

| Area | Test modules (glob / names) |
|------|----------------------------|
| Align / phase | `tests/test_*Align*.py`, `tests/test_*phase*.py` |
| STOS / refine | `tests/test_*stos*.py` (incl. `test_stos_registration_debug.py`), `tests/test_*refine*.py` |
| Arrange / masks | `tests/test_arrange.py`, `tests/test_overlapmasking.py` |

### Verification matrix (minimum)

| Change touches | Minimum checks |
|----------------|----------------|
| `phasecorrelation` / `batched_phase_correlation` | Unit tests for affected APIs; serial vs batched parity on a small fixture; microbench or compare script if perf-sensitive |
| `stos_brute` / refine shared | Relevant `test_*stos*` / `test_*refine*`; ≥100-tile section for final perf sign-off |
| `arrange_mosaic` / overlap masking | `test_arrange` / `test_overlapmasking` as applicable |
| New script or gate | Add row here; run it once before merge |

### Known gaps

| Gap | Notes |
|-----|--------|
| _(none recorded)_ | Add when creating new coverage debt; remove when filled |

## Same-commit sync

If this change adds/removes/renames inventory-affecting scripts or tests, update **this file** in the same commit (tables + matrix + known gaps).
