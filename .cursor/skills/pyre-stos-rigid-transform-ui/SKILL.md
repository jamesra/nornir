---
name: pyre-stos-rigid-transform-ui
description: >-
  Documents Pyre STOS rigid-transform UI semantics across Source (fixed/purple),
  Target (warped/green), and Composite views: command space, registration vs
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
| **Space.Source** | Fixed / mapped image native coordinates (purple layer) |
| **Space.Target** | Warped / section image native coordinates (green layer) |
| **ViewType.Source** | Standalone fixed panel (`Space.Source` commands) |
| **ViewType.Target** | Standalone warped panel (`Space.Target` commands) |
| **ViewType.Composite** | Overlay of both layers (`Space.Source` commands; draws in target space) |
| **Registration** | `TransformModel` fields: `angle`, `target_offset`, `source_space_center_of_rotation`, `forward_matrix` |
| **Display strategy** | `TransformDisplayStrategy.resolve_draw_state()` — GPU uniforms per panel pass |

Color convention in composite overlay shader: **purple = fixed**, **green = warped**.

Rigid model API (imageregistration):

- **Runtime model (Pyre STOS):** `CenteredSimilarity2DTransform` — uniform `scalar` between source and target; supports `ScaleWarpedAboutSourcePoint` / `ScaleFixed` (Shift+scroll on `ITransformRelativeScaling`, without Ctrl).
- **Load (Pyre only):** legacy `Rigid2DTransform` strings deserialize to `Rigid` / `RigidTranslation`; `StosWindow.loadStos` upgrades them to `CenteredSimilarity2DTransform` for editing. Global `LoadTransform` elsewhere keeps minimal types.
- **Save:** `CenteredSimilarity2DTransform.ToITKString()` writes `Rigid2DTransform_double_2_2` when `scalar ≈ 1`; writes full `CenteredSimilarity2DTransform_double_2_2` when scaled.
- `TranslateFixed(offset)` — move fixed in target space (+offset on `target_offset`)
- `TranslateWarped(offset)` — move warped in target space (−offset on `target_offset`)
- `RotateFixedAboutSourcePoint(rangle, source_pivot)` — composite rotation; pins `Transform(source_pivot)` via offset compensation
- `RotateSourcePoints(rangle, center_src)` — increase `angle`; set source rotation center

## Expected user-visible behavior (product invariants)

1. **Single transform** — Translate/rotate in any view updates the same registration; **all** views show the same alignment after the edit ends.
2. **Composite is the alignment truth check** — Purple and green should match standalone panels.
3. **Which layer moves** (rigid):
   - **Composite + translate/rotate** → user edits the **fixed (purple)** layer; green stays still during the gesture.
   - **Warped panel + translate** → user edits the **warped (green)** layer (translation only).
   - **Rigid rotation** → **Composite window only** (`rigid_rotation_locked` blocks Ctrl+scroll on Fixed and Warped standalone).
   - **Fixed standalone (rigid/grid)** → whole-layer translate/rotate is **blocked** (`fixed_image_manipulation_locked`).
4. **Rotation pivot** (rigid, composite only) — Ctrl+scroll rotates purple about the **cursor** via `RotateFixedAboutSourcePoint` (source pivot from `InverseTransform` of draw-world cursor).
5. **Relative scale** (rigid) — Shift+scroll (no Ctrl) on composite/target when model is `CenteredSimilarity2DTransform` calls `ScaleWarpedAboutSourcePoint` with the same composite pivot as Ctrl+scroll rotate. Do not use Alt+scroll on Windows (Qt delivers zero wheel delta while Alt is on the event).
6. **Zoom** — Mouse wheel without Ctrl zooms about cursor (`navigationcommandbase` lookat delta in active command space).
7. **Reset Transform** (STOS menu) — Rigid: zero offset, zero angle (`reset_rigid_transform`).

## Command routing

| Window | `view_type` | Command `space` | Rotate (rigid) | Translate API |
|--------|-------------|-----------------|----------------|---------------|
| Fixed | Source | Source | **Blocked** | `TranslateFixed` (blocked) |
| Warped | Target | Target | **Blocked** | `TranslateWarped` |
| Composite | Composite | **Source** | `RotateFixedAboutSourcePoint` | `TranslateFixed` |

Non-rigid transforms (mesh, grid, RBF) use **`MeshLikeDisplayStrategy`** (Delaunay tile path).

Composite `ImageTransformViewPanel` uses `CompositeTransformView` with
`display_space=Space.Target`. Both sub-FBOs render with `tween=1` (target space).

## Rendering architecture (rigid)

### Display strategy (`RigidDisplayStrategy`)

| Gesture | Set by | Editing layer | Non-editing layer during gesture |
|---------|--------|---------------|--------------------------------|
| `COMPOSITE_TRANSLATE` | translate drag, Source space | Live `forward_matrix` (purple) | Warped native frozen at gesture snapshot |
| `WARPED_TRANSLATE` | translate drag, Target space | Live `forward_matrix` (green) | Fixed standalone frozen at snapshot |
| `COMPOSITE_ROTATE` | Ctrl+scroll on Composite | Live `forward_matrix` after each `RotateFixedAboutSourcePoint` | Warped native frozen at snapshot |
| `Idle` | — | Live model | Live model |

Lifecycle:

- `TransformController.begin_interactive_edit(..., gesture=...)` → `begin_gesture` + matrix snapshot
- `TransformController.end_interactive_edit()` → `end_gesture` + coalesced `FireOnChangeEvent`
- `Translate()` during rigid drag → `on_translate_step()` + `notify_interactive_rigid_repaint()` + peer repaint for Target-space edits

### Draw path (`imagetransformview.py`)

Each pass calls `controller.resolve_draw_state(image_space, view_type, composite_fixed_align, tween)` and passes the result to `TextureShader.draw`. No ad hoc controller matrix branches in the view.

### Shader (`texture_shader.py`)

Rigid path maps native tile corners through `rigid_source_to_target`. Overlay uniforms (`rigid_*_display_matrix`, `rigid_interactive_native_shift`) remain in the shader but are **identity/zero** for rigid STOS (model-authoritative).

## Cross-view sync checklist (before merging UI changes)

1. **Composite rotate** (rigid) — purple pivots on cursor; green unchanged during gesture; no teleport on release.
2. **Warped panel** (rigid) — Ctrl+scroll does **not** rotate; translate still works.
3. **Composite translate** — purple moves; green still; no jump on mouse release.
4. **Warped translate** — green moves; composite updates live (`repaint_peer_stos_gl_panels`).
5. **Cross-view** — all panels aligned after each gesture ends.
6. **Reset Transform** — all three views return to identity alignment.
7. **Zoom** — cursor-centered in each panel.

## Policy helpers (`transform_edit_policy.py`)

| Function | When true |
|----------|-----------|
| `fixed_image_manipulation_locked` | Standalone Fixed panel: no layer translate/rotate (rigid/grid) |
| `rigid_rotation_locked` | Not Composite + rigid: no Ctrl+scroll rotation |
| `wheel_rotate_locked` | Combines fixed-panel lock + rigid composite-only rotation |

## Key files

| File | Role |
|------|------|
| `pyre/controllers/transform_display.py` | `TransformDisplayStrategy`, `RigidDisplayStrategy`, registry |
| `pyre/controllers/transformcontroller.py` | Registration calls, strategy delegation, interactive edit |
| `pyre/views/imagetransformview.py` | Calls `resolve_draw_state` |
| `pyre/views/compositetransformview.py` | Dual FBO composite draw |
| `pyre/gl_engine/shaders/texture_shader.py` | Vertex transforms |
| `pyre/commands/navigationcommandbase.py` | Wheel zoom/rotate |
| `pyre/commands/stos/translaterigidcommand.py` | Drag translate |
| `pyre/transform_edit_policy.py` | Gesture policy matrix |
| `nornir-pyre/docs/adding_transform_display_strategy.md` | How to plug in new transform types |

## Agent workflow

1. Read this skill before editing files above.
2. State which **invariant** your change affects.
3. Put display logic in **`TransformDisplayStrategy`**, not new booleans in `imagetransformview`.
4. Any new gesture needs `begin_gesture` / `end_gesture` wiring and checklist verification.
5. After behavior changes, run the cross-view checklist and update this skill if lifecycle rules change.
