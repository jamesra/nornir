---
name: cupy-missing-api-bugfix
description: >-
  When fixing bugs caused by missing or incompatible CuPy APIs (implicit NumPy
  conversion, AttributeError on cupy arrays, unsupported calls under a CuPy
  backend), prefer a CuPy-and-NumPy–compatible fix before forcing a pure NumPy
  path. Use when debugging imageregistration array code, CuPyX vs SciPy
  choices, or host/device boundaries.
---

# CuPy missing API — bugfix order

## Source of truth

Follow **`.cursor/rules/Numpy-CuPy-compatibility.mdc`**, especially **Bug fixes when CuPy lacks an implementation**, plus the rest of that file for `xp`, `get_array_module`, transfers, and CuPyX.

## Workflow (short)

1. **First** try a solution that preserves **numpy in → numpy out** and **cupy in → cupy out** where APIs allow: `cp.get_array_module`, `cupyx.scipy.get_array_module`, device-side equivalents, or a small dispatcher.
2. **Then** consider a **narrow host boundary** for only the unsupported step, with the rest of the pipeline staying on the input backend when practical.
3. **Last** adopt a **whole-pipeline NumPy / CPU-only** path when there is no reasonable dual-backend option, the work is inherently host-based, or the existing rule’s small-data / environment exceptions apply—**document** that boundary in code.

Do not default to “convert everything to NumPy” as the first fix when a dual-backend or partial-boundary fix is feasible.
