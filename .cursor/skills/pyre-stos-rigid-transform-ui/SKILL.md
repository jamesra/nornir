---
name: pyre-stos-rigid-transform-ui
description: >-
  Documents Pyre STOS rigid-transform UI semantics across Source (mapped),
  Target (control), and Composite views: command space, registration vs
  display strategy, interactive-edit freeze rules, cross-view sync, and repaint.
  Use when editing rigid translate/rotate/zoom in nornir-pyre, debugging view
  mismatch, or before changing transformcontroller, transform_display,
  imagetransformview, texture_shader, or navigation commands.
---

# Pyre STOS rigid transform UI

One **shared** `TransformController` / `IRigidTransform` model drives all STOS
windows. Display is resolved by **`RigidDisplayStrategy`** (`pyre/controllers/transform_display.py`):
**model-authoritative** matrices from `forward_matrix`, with gesture snapshots only
to **freeze the non-editing layer** during a drag or wheel notch.

## Vocabulary

| Term | Meaning |
|------|---------|
| **Space.Source** | Mapped / moving image native coordinates (`SourcePoints`) |
| **Space.Target** | Control / reference image native coordinates (`TargetPoints`) |
| **ViewType.Source** | Standalone mapped-image panel (`Space.Source` commands) |
| **ViewType.Target** | Standalone control-image panel (`Space.Target` commands) |
| **ViewType.Composite** | Overlay in target display space (`Space.Source` commands for rigid) |
| **Registration** | `TransformModel` fields: `angle`, `target_offset`, `source_space_center_of_rotation`, `forward_matrix` |
| **Display strategy** | `TransformDisplayStrategy.resolve_draw_state()` — GPU uniforms per panel pass |

Color convention in composite overlay shader: **magenta = source**, **green = target**.

### Composite display invariant

- **Target layer** — native target coordinates; does not move on screen.
- **Source layer** — warped into target display space; moves during alignment.

### Image tile mesh (mesh / grid / RBF)

| View | Tile mesh | Draw tween |
|------|-----------|------------|
| Target panel | Static quads (native target) | `Space.Target` |
| Source panel | Static quads (native source) | `Space.Source` |
| Composite target FBO | Static quads | `Space.Target` |
| Composite source FBO | Deformable CP mesh (`warp_into_target_display`) | `Space.Source` (tween 0 → TargetPoints) |

Texture shader: `mix(target_pos, source_pos, tween)` with packed `(TargetPoints, SourcePoints)`. **Do not** draw the Target image with a CP warp mesh — moving `TargetPoints` folds Delaunay and shatters the green layer.

### Control point space (mesh / grid / RBF)

Pyre **`Space`** matches registration column names:

| Pyre `Space` | Registration columns |
|--------------|------------------------|
| `Space.Source` | `SourcePoints` |
| `Space.Target` | `TargetPoints` |

`MovePoint`, `GetPoints`, `SetPoint`, `ControlPointMap`, and control-point glyph tween all use this mapping. Same mapping as `NearestPoint`, `TryDrag`, and `Translate` (`TranslateWarped` / `TranslateFixed`).

Control-point GL buffer layout: columns `0:2` = `TargetPoints`, `2:4` = `SourcePoints` (registration convention). Shader `mix(point_source_offset, point_target_offset, tween)` yields **tween 0 → SourcePoints**, **tween 1 → TargetPoints**. `shader_tween_for_panel_space`: Source panel → 0.0; Target panel → 1.0. Composite mesh/grid draws `Transform(SourcePoints)` in display space (tween 0, source columns overridden).

All STOS panels share one control-point GL buffer per `TransformController`; composite draw must re-sync from `controller.points` after override (never restore already-swapped XY through `PointView.points` getter/setter).

On composite (mesh/grid), hit-testing uses **target display space** at `Transform(SourcePoints)` via `composite_display.py`; `ControlPointMap` special-cases `ViewType.Composite`. Composite CP drags apply deltas in **Target** space (`TranslateControlPointCommand._edit_space_for_translate`) because glyphs are display-space and grid transforms only edit `TargetPoints`.

Rigid model API (imageregistration):

- **Runtime model (Pyre STOS):** `CenteredSimilarity2DTransform`
- `TranslateWarped(offset)` — move mapped section in target space
- `TranslateFixed(offset)` — move control/reference in target space
- `RotateSourcePoints` / `RotateFixedAboutSourcePoint` — source vs composite pivot rotation

## Expected user-visible behavior (product invariants)

1. **Single transform** — Translate/rotate in any view updates the same registration.
2. **Composite is the alignment truth check** — Source and target overlays should match standalone panels.
3. **Composite default: adjust mapped (source) layer** — Source overlay warped into target space moves; target reference stays static. On mouse-up after rigid translate, rebase composite `camera.lookat` so target-display framing does not snap onto the moved source (`display_lookat_for_composite` while frozen → `lookat_from_display_position` after `end_interactive_edit`).
4. **Which layer moves** (rigid):
   - **Composite + translate/rotate** → **source overlay** moves; **target layer frozen** during gesture.
   - **Source panel + translate** → mapped layer moves (`TranslateWarped`).
   - **Target panel** → whole-layer translate/rotate **blocked** for rigid/grid.
   - **Rigid rotation** → **Composite window only** (`rigid_rotation_locked`).
5. **Rotation pivot** (rigid, composite) — Ctrl+scroll passes **source-space cursor** (`point_pair.source`, already `InverseTransform(display)`) to `Rotate`; `TransformController` calls `RotateFixedAboutSourcePoint` to pin `Transform(pivot)` in target space.
6. **Relative scale** — Shift+scroll on composite/source when model is `CenteredSimilarity2DTransform`. Pivot is **source-space cursor** (`point_pair.source`); `ScaleWarped` calls `ScaleWarpedAboutSourcePoint` (do not InverseTransform again). Composite then adjusts camera lookat so the pinned target point stays under the cursor.
7. **Zoom** — Mouse wheel without Ctrl zooms about cursor.

## Command routing

| Window | `view_type` | Command `space` | Rotate (rigid) | Translate API |
|--------|-------------|-----------------|----------------|---------------|
| Source | Source | Source | **Blocked** | `TranslateWarped` |
| Target | Target | Target | **Blocked** | `TranslateFixed` (blocked) |
| Composite | Composite | **Source** | `RotateFixedAboutSourcePoint` | `TranslateWarped` |

Non-rigid transforms use **`MeshLikeDisplayStrategy`** (Delaunay tile path).

## Shader uniforms (rigid)

| Uniform | Semantics |
|---------|-----------|
| `rigid_native_is_target` | Target-slot image drawn in native target coords |
| `rigid_source_in_target_display` | Composite: warp source FBO into target display space |
| `rigid_source_display_matrix` / `rigid_target_display_matrix` | Gesture overlay matrices |

## Related files

- `pyre/controllers/transformcontroller.py` — Space routing
- `pyre/controllers/transform_display.py` — `RigidDisplayStrategy`, freeze logic
- `pyre/views/composite_display.py` — target display space helpers
- `pyre/views/compositetransformview.py` — dual FBO composite draw
- `pyre/gl_engine/shaders/texture_shader.py` — rigid uniforms
- `pyre/transform_edit_policy.py` — panel lock helpers

## Convert to grid

`ConvertToGridDialog` offers **by spacing** (Y/X spacing between control points) or **by dimensions** (rows/columns). Do not expose refine-grid `cell_size` for conversion; pass `grid_spacing` or `grid_dims` to `ConvertTransform`.
