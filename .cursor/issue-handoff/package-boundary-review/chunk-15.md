# Chunk 15 — Pyre

## Findings

- Image load goes through `nornir_imageregistration.LoadImage` in `ImageViewModel`. That is the right dependency. Display pad/tile math stays in the view model because it exists to fit GL textures, not to build a volume pyramid.
- `ResizeToPowerOfTwo` names `tile_height` / `tile_width` and then multiplies columns by height and rows by width (`newwidth = NumCols * tile_height`). Square tiles hide it. Do not “fix” it in this pass; it is a long-lived display path and the axis naming is easy to misread.
- `pyproject.toml` depends on `nornir_buildmanager`. The only import is `pyre/__main__.py` inside `--smoke-test`, next to imageregistration, pools, and shared. The GUI does not need buildmanager to register a point. Dropping the dependency is a packaging change: the frozen smoke test would stop proving that buildmanager imports. Say so if it is removed.
- Pyre must not be imported by buildmanager or imageregistration. Current direction matches that.

## Carry forward

Buildmanager dependency is smoke-test only.
