---
name: STOS explorer delete auto
overview: Add Delete-key handling in the Pyre Stos Directory window to remove only the automatic `.stos` file for the selected row, with a Yes/No confirmation dialog (Enter or Yes confirms). Manual overrides in `Manual/` are never touched. Manual-only rows (auto deleted) use a darker yellow list color; Auto file-source loading must resolve to the manual file when no automatic file exists.
todos:
  - id: delete-helpers
    content: Add delete helpers and list event filter in stosfilebrowser.py
    status: completed
  - id: manual-only-styling
    content: Darker yellow font for manual-only rows; add row helper on StosBrowserRow
    status: completed
  - id: auto-load-fallback
    content: Harden _load_stos_at_index and navigation for manual-only rows under Auto source
    status: completed
  - id: delete-tests
    content: "Tests: delete flow, manual-only styling, auto-load when auto missing"
    status: completed
isProject: false
---

# Delete automatic STOS from Stos Directory

## Context

The ".stos explorer" is [`StosFileBrowserWindow`](nornir-pyre/pyre/ui/windows/stosfilebrowser.py) ("Stos Directory"). It already models each list row as a [`StosBrowserRow`](nornir-pyre/pyre/stos_manual_paths.py) with separate `auto_path` (group folder) and `manual_path` (`Manual/` override).

```82:96:nornir-pyre/pyre/stos_manual_paths.py
def resolve_default_load_path(auto_path: str | None, manual_path: str | None) -> str | None:
    """Prefer the manual override when present."""
    if manual_path and os.path.isfile(manual_path):
        return manual_path
    return auto_path

def resolve_load_path(..., source: StosFileSource) -> str | None:
    if source == StosFileSource.auto:
        return resolve_default_load_path(auto_path, manual_path)
```

Today, any row with a manual override uses the same gold color (`#c9a227`) and `[Manual]` suffix. After deleting the automatic file, the row becomes **manual-only** (manual exists, auto missing) — a distinct state that needs darker yellow styling and verified load behavior.

## Behavior

### Delete key

| Situation | Delete key action |
|-----------|-------------------|
| Row has `auto_path` on disk | Show confirmation; on Yes, delete **only** `auto_path` |
| Row is manual-only (`auto_path` is None) | No-op with brief info message ("No automatic STOS file to delete") |
| `BrowseMode.flat_manual` (user opened `Manual/` directly) | Same as manual-only — never delete |
| User presses No / Escape | Cancel; no filesystem change |

**Confirmation dialog**

- Use `QMessageBox.question` (same pattern as [`defaulttransformcommand.py`](nornir-pyre/pyre/commands/defaulttransformcommand.py)).
- Buttons: **Yes** | **No**.
- **Default button: Yes** so Enter confirms without an extra click.
- Message should name the basename and show the automatic file path; explicitly note the manual override is not affected when one exists.

**After successful delete**

1. `rescan()` to refresh rows from disk (existing public method).
2. Preserve selection on the same `basename` when the row still exists (manual override remains); otherwise clamp to a valid index.
3. Row re-renders as **manual-only** (darker yellow; see below).
4. On `OSError`, show `QMessageBox.warning` with the error; leave the list unchanged.

**Loaded STOS session:** Out of scope for v1 — if the user had the deleted automatic file open in `StosWindow`, the editor may show a stale transform until they navigate.

### Manual-only row styling (new)

Distinguish two manual states in `stos_group` browse mode:

| State | Condition | List color | Label |
|-------|-----------|------------|-------|
| Manual override (auto still present) | `has_manual` and `has_auto` | Existing gold `#c9a227` | `{basename} [Manual]` |
| Manual-only (auto deleted / never existed) | `has_manual` and not `has_auto` | **Darker gold** e.g. `#8b6914` | `{basename} [Manual]` |

Add a small helper on [`StosBrowserRow`](nornir-pyre/pyre/stos_manual_paths.py):

- `is_manual_only` — manual file exists on disk and automatic file does not.

Use this in `_populate_list`, `minimum_layout_width`, and tooltip text (optional: append "(automatic missing)" in tooltip for manual-only rows).

Constants on `StosFileBrowserWindow`:

- `_manual_override_color` — keep `#c9a227`
- `_manual_only_color` — new darker shade `#8b6914`

### Automatic loading when auto file is missing (new)

**Path resolution already correct** for `StosFileSource.auto`: `resolve_default_load_path(None, manual_path)` returns the manual path.

Harden the **browser load path** so navigation and open never fail on manual-only rows when Auto is the effective source:

1. **`_load_stos_at_index`** — resolve load path with a small fallback chain:
   - Try the user's selected source (`_source_for_load()`).
   - If that returns `None` and `StosFileSource.auto` would resolve a path, use the auto path instead and sync the file-source selector to Auto (same as `_update_source_selector_for_current_row` already does on selection change).
   - Only show "STOS not found" when **no** variant exists.

   This fixes a gap where `+`/`-` navigation calls `_load_stos_at_index` **before** `currentRowChanged` runs, so a persisted **Original** source can error on manual-only rows even though Auto would load the manual file.

2. **`_update_source_selector_for_current_row`** — no semantic change needed; keep disabling **Original** when `has_auto` is False and leaving **Auto** enabled (Auto still loads manual).

3. **Tests** in [`test_stos_manual_paths.py`](nornir-pyre/tests/test_stos_manual_paths.py):
   - `resolve_load_path(None, manual, StosFileSource.auto)` → manual (may already exist).
   - `scan_stos_browser_rows` manual-only entry: `is_manual_only` is True, `default_load_path` is manual.

4. **Browser test**: with File Source = Auto, `_load_stos_at_index` on a manual-only row loads the manual path (mock `StosWindow.loadStos`).

## Implementation

### 1. [`stos_manual_paths.py`](nornir-pyre/pyre/stos_manual_paths.py)

- Add `StosBrowserRow.is_manual_only` property.
- Add unit tests for manual-only row scan and auto-source resolution.

### 2. [`stosfilebrowser.py`](nornir-pyre/pyre/ui/windows/stosfilebrowser.py)

Delete helpers:

- `_row_can_delete_automatic(row) -> bool` — `browse_mode != flat_manual` and `auto_path` is a regular file.
- `_confirm_delete_automatic(row) -> bool` — `QMessageBox.question(..., default=Yes)`.
- `_delete_automatic_at_index(index: int) -> None` — confirm, `os.remove(auto_path)`, `rescan()`, restore selection by basename.

Styling:

- `_row_list_color(row)` — returns `_manual_only_color` vs `_manual_override_color` vs default.
- Apply in `_populate_list` (replace single `has_manual_override` color branch).

Loading:

- `_resolve_load_path_for_row(row, source) -> str | None` — requested source, then Auto fallback.
- Use in `_load_stos_at_index`; when fallback used, call `_file_source_selector.set_source(StosFileSource.auto)` and persist settings.

Keyboard:

- Event filter on `_list_widget` for `Qt.Key.Key_Delete` → `_delete_automatic_at_index(self._current_index)`.

Update module docstring for Delete key, manual-only color, and Auto load fallback.

### 3. Tests — [`test_stos_file_browser_delete.py`](nornir-pyre/tests/test_stos_file_browser_delete.py) (new)

- Delete guards and successful delete (auto gone, manual remains).
- Cancel path.
- Manual-only row gets darker color constant (compare `item.foreground().color()`).
- Auto-source load on manual-only row succeeds (mock `StosWindow.loadStos`).

## Flow

```mermaid
flowchart TD
    keyDelete[Delete key on list row] --> hasAuto{auto_path exists?}
    hasAuto -->|no| inform[Show info: nothing to delete]
    hasAuto -->|yes| confirm[QMessageBox Yes/No default Yes]
    confirm -->|No| done[Cancel]
    confirm -->|Yes| remove[os.remove auto_path]
    remove --> rescan[rescan folder]
    rescan --> style[Row: manual-only darker yellow]
    style --> select[Restore selection by basename]

    loadRow[Load row at index] --> trySource{selected source resolves?}
    trySource -->|yes| open[StosWindow.loadStos]
    trySource -->|no| tryAuto{Auto source resolves?}
    tryAuto -->|yes| syncAuto[Set selector to Auto and open manual]
    tryAuto -->|no| error[STOS not found dialog]
```

## Files touched

| File | Change |
|------|--------|
| [`nornir-pyre/pyre/stos_manual_paths.py`](nornir-pyre/pyre/stos_manual_paths.py) | `is_manual_only` property |
| [`nornir-pyre/pyre/ui/windows/stosfilebrowser.py`](nornir-pyre/pyre/ui/windows/stosfilebrowser.py) | Delete, styling, load fallback, event filter |
| [`nornir-pyre/tests/test_stos_manual_paths.py`](nornir-pyre/tests/test_stos_manual_paths.py) | Manual-only + auto-load tests |
| [`nornir-pyre/tests/test_stos_file_browser_delete.py`](nornir-pyre/tests/test_stos_file_browser_delete.py) | Delete, color, browser load tests |
