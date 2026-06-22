# ir-blob C++ → Python parity checklist

Audit of legacy `ir-blob` ([`/legacycode/code/ir-tools/ir-blob.cxx`](/legacycode/code/ir-tools/ir-blob.cxx))
mapped to Python in [`nornir_imageregistration/nornir_imageregistration/blob_filter.py`](../nornir-imageregistration/nornir_imageregistration/blob_filter.py).

## 1. CLI and pipeline defaults

| # | C++ (`ir-blob.cxx`) | Python / buildmanager | Parity |
|---|---------------------|----------------------|--------|
| 1.1 | `-sh 1` shrink on load (`std_tile`, default 1) | Input already at target downsample in pipeline | OK |
| 1.2 | `-r` radius (default 2 in tool, **9** in [`Pipelines.xml`](../nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml)) | `radius` / `-Radius` | OK |
| 1.3 | `-median` ITK MedianImageFilter radius (default 0, **7** in IDoc pipeline) | `median_radius` | **Port** (nearest boundary) |
| 1.4 | `-max` threshold (default 3) | `max_value` | OK |
| 1.5 | `-mask` optional; else `std_mask` (all valid) | `mask_path` or all-true | OK |

## 2. Median prefilter (`median()`, `common.hxx` L6127)

| # | C++ | Python target | Parity |
|---|-----|---------------|--------|
| 2.1 | ITK `MedianImageFilter` radius `[median, median]` (Neumann edges) | `scipy.ndimage.median_filter(..., size=2r+1, mode="nearest")` | **Port** |
| 2.2 | Skip when `median_radius == 0` | Same | OK |

## 3. Local variance (`calc_variance`, `ir-blob.cxx` L63–149)

| # | C++ | Python target | Parity |
|---|-----|---------------|--------|
| 3.1 | Window width/height `(2r+1)` shifted to stay in bounds | `_window_bounds_1d` + per-pixel slices | **Port** |
| 3.2 | Mean/variance over **mask-true** samples only | Same | **Port** |
| 3.3 | `mass==0` → variance pixel left at `float_max` sentinel | `_VARIANCE_SENTINEL` | **Port** |
| 3.4 | Population variance `sum((p-mean)²)/mass` | Same | **Port** |

## 4. Blob enhancement (`enhance_blobs`, L251–420)

| # | C++ | Python target | Parity |
|---|-----|---------------|--------|
| 4.1 | Collect valid variance samples (`!= float_max`), `qsort`, median at `[count/2]` | `_global_variance_median` | **Port** |
| 4.2 | `metric = min(threshold, (median+1)/(v+1))` for valid pixels | `_enhance_blobs` | **Port** |
| 4.3 | Invalid pixels → **mean metric** over valid pixels | Not zero | **Port** |
| 4.4 | Do **not** divide by threshold before normalize | Removed early `/ max` | **Port** |

## 5. Output normalization (`normalize(image,1,1,0,255,mask)`, `common.hxx` L6198–6321)

| # | C++ | Python target | Parity |
|---|-----|---------------|--------|
| 5.1 | Masked mean/sigma (`StatisticsImageFilterWithMask`, unbiased variance) | `_normalize_with_mask` | **Port** |
| 5.2 | `(x - mean) / sigma` on full image | Same | **Port** |
| 5.3 | Clip to `[-3, 3]` | `_clip` | **Port** |
| 5.4 | Linear remap global min/max → `[0, 255]` | `_remap_min_max_inplace` | **Port** |
| 5.5 | Save 8-bit PNG (`save<native_image_t>`) | `SaveImage(..., bpp=8)` | OK |

## 6. Golden fixtures

Legacy PNG testdata: `/legacycode/code/BuildScript/Test/Data/PlatformRaw/PNG/6872/`

- Input: `0001_LeveledShadingCorrectedgfp_mosaic_1.png`
- Mask: `0001_LeveledShadingCorrectedgfp_mask_1.png`
- Golden: `0001_LeveledShadingCorrectedgfp_blob_1.png`
- Params: `r=3, median=5, max=3` (legacy 6872 fixture; BuildScript `Channel.py` default median is 3)

Tests crop a central 512×512 region for CI speed; full-image optional via env.

## 7. Cache invalidation (operators)

After parity fix, delete existing `Blob` filter images or invalidate input checksums before re-running `CreateBlobFilter` so STOS brute uses new blob PNGs.

Re-run `TestIDocBuild` from `RunCreateBlobFilter` onward (or use `IDocBuildTestBootstrapDebugging` with earlier steps commented out), then compare `StosBrute16` overlays before/after.

IDoc pipeline params (from [`Pipelines.xml`](../nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml)): `r=9`, `median=7`, `max=3`.

## 8. Validation status

- Golden regression: legacy 6872 fixture passes at `r=3`, `median=5`, `max=3` (≤1 DN vs precomputed PNG).
- IDoc repro snapshot under `TESTOUTPUTPATH/Repros/IDocBuildTest` predates blob generation; full slice-to-slice validation requires re-running bootstrap from `RunCreateBlobFilter`.
- Optional exe parity: configure `NORNIR_LEGACY_IR_BLOB` + fixture paths; thresholds default to MAE ≤ 0.01 and P99 ≤ 1 DN.
