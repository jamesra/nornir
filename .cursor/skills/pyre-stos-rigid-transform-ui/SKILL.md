---
name: pyre-stos-rigid-transform-ui
description: >-
  Documents Pyre STOS rigid-transform UI semantics across Source (fixed/purple),
  Target (warped/green), and Composite views: command space, registration vs
  display overlays, interactive-edit freeze rules, cross-view rebasing, and
  repaint. Use when editing rigid translate/rotate/zoom in nornir-pyre,
  debugging view mismatch, or before changing transformcontroller,
  imagetransformview, texture_shader, or navigation commands.
---

# Pyre STOS rigid transform UI

One **shared** `TransformController` / `IRigidTransform` model drives all STOS
windows. UI code splits **registration** (persisted transform) from **display
overlays** (per-panel GPU matrices and shifts). Cross-view bugs usually mean
those layers diverged or a view did not repaint.

## Vocabulary

| Term | Meaning |
|------|---------|
| **Space.Source** | Fixed / mapped image native coordinates (purple layer) |
| **Space.Target** | Warped / section image native coordinates (green layer) |
| **ViewType.Source** | Standalone fixed panel (`Space.Source` commands) |
| **ViewType.Target** | Standalone warped panel (`Space.Target` commands) |
| **ViewType.Composite** | Overlay of both layers (`Space.Source` commands; draws in target space) |
| **Registration** | `TransformModel` fields: `angle`, `target_offset`, `source_space_center_of_rotation`, `forward_matrix` |
| **Display overlay** | Controller-owned GPU state that may differ from `forward_matrix` during/after edits |

Color convention in composite overlay shader: **purple = fixed**, **green = warped**.

Rigid model API (imageregistration):

- `TranslateFixed(offset)` — move fixed in target space (+offset on `target_offset`)
- `TranslateWarped(offset)` — move warped in target space (−offset on `target_offset`)
- `RotateFixed(rangle, center_tgt)` — decrease `angle`; rotate `target_offset` about **target-space** pivot
- `RotateSourcePoints(rangle, center_src)` — increase `angle`; set `source_space_center` to **source-space** pivot

## Expected user-visible behavior (product invariants)

1. **Single transform** — Translate/rotate in any view updates the same registration; **all** views show the same alignment after the edit ends.
2. **Composite is the alignment truth check** — Purple (fixed transformed into target space) and green (warped native) should match standalone panels.
3. **Which layer moves** (rigid):
   - **Composite + translate/rotate** → user edits the **fixed (purple)** layer; green stays still during the gesture.
   - **Warped panel + translate** → user edits the **warped (green)** layer (translation only).
   - **Rigid rotation** → **Composite window only** (`rigid_rotation_locked` blocks Ctrl+scroll on Fixed and Warped standalone).
   - **Fixed standalone (rigid/grid)** → whole-layer translate/rotate is **blocked** (`fixed_image_manipulation_locked`).
4. **Rotation pivot** (rigid, composite only) — Ctrl+scroll rotates purple about the **cursor** (target-space world position under the mouse).
5. **Zoom** — Mouse wheel without Ctrl zooms about cursor (`navigationcommandbase` lookat delta in active command space).
6. **Reset Transform** (STOS menu) — Rigid: zero offset, zero angle, clear display overlays (`reset_rigid_transform`).

## Command routing

| Window | `view_type` | Command `space` | Rotate (rigid) | Translate API |
|--------|-------------|-----------------|----------------|---------------|
| Fixed | Source | Source | **Blocked** | `TranslateFixed` (blocked) |
| Warped | Target | Target | **Blocked** | `TranslateWarped` |
| Composite | Composite | **Source** | `RotateFixed` + fixed display | `TranslateFixed` |

Non-rigid transforms (mesh, grid, etc.) are not gated by `rigid_rotation_locked`; mesh may still rotate on the warped panel.

Composite `ImageTransformViewPanel` uses `CompositeTransformView` with
`display_space=Space.Target`. Both sub-FBOs render with `tween=1` (target space).

## Rendering architecture (rigid)

### Shader (`texture_shader.py`)

Tile corners are **native** (source tiles on fixed path, target tiles on warped path).

For rigid path:

1. Source-native corners → `rigid_source_to_target` → warped slot position.
2. Composite source FBO: `rigid_fixed_warped_into_target` copies warped slot to fixed slot (purple at transformed position).
3. **Warped layer** (standalone **or** composite target FBO): `rigid_interactive_native_shift` then `rigid_warped_display_matrix` on green native corners.
4. **Composite source FBO**: `rigid_fixed_display_matrix` on purple after forward transform.

### Display state (`TransformController`)

| State | Purpose |
|-------|---------|
| `rigid_warped_display_baseline` | `target_offset` snapshot when display overlays were reset |
| `rigid_warped_display_matrix` | Cumulative warped-panel rotation (mesh / non-rigid; unused for rigid warped-panel rotation) |
| `rigid_fixed_display_baseline_matrix` | Frozen `forward_matrix` for composite purple |
| `rigid_fixed_display_matrix` | Incremental composite purple rotation; committed into baseline on `end_interactive_edit` |
| `rigid_matrix_at_edit_start` | Snapshot for **freezing** the non-edited layer during interactive edit |

### Rebase / sync at `end_interactive_edit`

After each interactive edit (wheel notch, translate release):

1. `_commit_rigid_fixed_display_matrix()` — fold pending composite-purple rotation into `rigid_fixed_display_baseline_matrix`.
2. **Target-space edit** (warped panel): `_refresh_rigid_fixed_display_baseline_from_model()` so composite purple catches registration changes from warped edits.
3. **Source-space edit without fixed display rotation** (e.g. composite translate): same refresh from live `forward_matrix`.
4. **Source-space rotate on composite**: commit only (baseline already includes rotation); do not overwrite from model in the same tick.
5. `FireOnChangeEvent()` — coalesced listener notification; all STOS `ImageTransformViewPanel` instances repaint their GL canvas.

Full reset: `_sync_rigid_warped_display_baseline()` on transform load/replace and `reset_rigid_transform`.

### Per-view draw selection (`imagetransformview.py`)

| Draw context | `rigid_forward` | Extra uniforms |
|--------------|---------------|----------------|
| Fixed standalone | Live `forward_matrix` | — |
| Warped standalone | Live (frozen during Target interactive edit; unused on native corners) | `shift = target_offset − baseline`, `rigid_warped_display_matrix` |
| Composite source FBO | **`rigid_fixed_display_baseline_matrix`** | `rigid_fixed_display_matrix` |
| Composite target FBO | Live / frozen per interactive rules | Same warped `shift` + `rigid_warped_display_matrix` as standalone |

### Interactive-edit freeze

While `interactive_edit_in_progress`:

- **Editing layer** uses live registration updates + that layer's display overlay.
- **Other layer** in composite uses `rigid_matrix_at_edit_start` when sub-view `image_space != interactive_edit_space`, except composite source FBO always uses the fixed display baseline path (purple stays on stale baseline until edit ends — intentional).

`begin_interactive_edit` / `end_interactive_edit` wrap each wheel tick and drag segment.

### Cross-view repaint

`ImageTransformViewPanel` subscribes to `TransformController.AddOnChangeEventListener` and calls `glcanvas.update()` so edits in one window refresh the others without requiring focus on that window.

## Coordinate helpers

`NavigationCommandBase.get_world_positions(e)`:

- `Space.Source` panel: `source = camera position`, `target = Transform(source)`
- `Space.Target` panel: `target = camera position`, `source = InverseTransform(target)`

Rotation pivot passed to display recorders (composite / rigid fixed path only):

- `center = point_pair.source` (camera world = target-space vertex coords under cursor on composite)

Composite fixed display rotation uses **−rangle** in `record_fixed_display_rotation` to match `RotateFixed` angle sign.

## Cross-view sync checklist (before merging UI changes)

1. **Composite rotate** (rigid) — purple pivots on cursor; green unchanged during gesture.
2. **Warped panel** (rigid) — Ctrl+scroll does **not** rotate; translate still works.
3. **Composite translate** — purple moves; green still.
4. **Warped translate** — green moves in Warped; composite alignment updates live (purple baseline refreshed each step).
5. **Cross-view** — composite and warped translate stay aligned; composite rotation updates all views after each notch.
6. **Reset Transform** — all three views return to identity alignment.
7. **Zoom** — cursor-centered in each panel.

## Policy helpers (`transform_edit_policy.py`)

| Function | When true |
|----------|-----------|
| `fixed_image_manipulation_locked` | Standalone Fixed panel: no layer translate/rotate (rigid/grid) |
| `rigid_rotation_locked` | Not Composite + rigid: no Ctrl+scroll rotation |

## Key files

| File | Role |
|------|------|
| `pyre/controllers/transformcontroller.py` | Registration calls, display matrices, interactive edit, rebase |
| `pyre/views/imagetransformview.py` | Per-panel matrix/uniform selection |
| `pyre/views/compositetransformview.py` | Dual FBO composite draw |
| `pyre/gl_engine/shaders/texture_shader.py` | Vertex transforms |
| `pyre/commands/navigationcommandbase.py` | Wheel zoom/rotate, `get_world_positions` |
| `pyre/commands/stos/translaterigidcommand.py` | Drag translate |
| `pyre/ui/widgets/imagetransformviewpanel.py` | Cross-view repaint on `FireOnChangeEvent` |
| `pyre/transform_edit_policy.py` | Fixed standalone lock; **rigid rotation composite-only** |
| `pyre/ui/windows/stoswindow.py` | Per-window `space`, menus |
| `nornir_imageregistration/transforms/rigid.py` | Registration math |

## Agent workflow

1. Read this skill before editing files above.
2. State which **invariant** your change affects.
3. Any new display state needs a **rebase hook** in `end_interactive_edit` or `_sync_rigid_warped_display_baseline` and must trigger `FireOnChangeEvent`.
4. Do not fix one panel by skipping display overlays on another.
5. After behavior changes, run the cross-view checklist and update this skill if lifecycle rules change.
