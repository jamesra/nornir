# Pyre "Estimate Scale" (set aside 2026-11-20)

James asked for Registration > Estimate Scale on rigid transforms: measure the scale, apply only it, Ctrl+Z undoes it.
The UI and undo work (`pyre-estimate-scale.patch` against nornir-pyre 5c1d1be, tests in `pyre-estimate-scale-test.py`),
but the measurement is not trustworthy, so it was not committed.

Measured on the RC3 pack (`C:\Temp\Nornir\rc3_pyre_pack\RC3v2_pyre`, ds32), StosBrute at the transform's angle:

| pair | scale of the Grid32 as rigid | global search (no hint) | local refine from a seed |
|------|------------------------------|-------------------------|--------------------------|
| 294-296 | 0.968 | 0.9986 | 0.9986 from 1.0 and 0.997 |
| 325-327 | 1.102 | 1.12 (range edge) | 1.00 from 1.0 |
| 1025-1026 | 0.954 | 0.906 | 1.01 from 1.0, 0.906 from 0.95, 1.05 from 1.05 |
| 258-259 | 0.921 | 1.090 | - |

The local refine (`RefineRigidTransformLocal`, also Refine Translation and Scale) stays near its seed; the global
search often lands on the [0.90, 1.12] edge. The radial FFT seed was out of band on three pairs. A scale estimator
that converges from different seeds is needed first (and a reference: 1025-1026 and 258-259 have open Grid32 fixes).
