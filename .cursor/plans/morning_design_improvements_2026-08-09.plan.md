# Morning design improvements (from overnight bug review)

**Created:** 2026-08-09 (overnight session)  
**Status:** Proposed — overnight complete (~12:08 local); review on waking  
**Context:** Overnight passes 1–11 landed many correctness fixes across shared/pools/imageregistration/buildmanager (see `.cursor/overnight-bug-review-progress.md`). Remaining work is structural debt that overnight patches kept touching asymmetrically. Review behavioral notes before shipping volumes (checksum / GenName / STOS rebase / DataChecksum list). Changes are uncommitted until you ask.
## Goals

Turn recurring overnight failure modes into intentional designs so the next bug pass is smaller and less “fix one twin, miss the other.”

## Themes

### 1. CPU / GPU dual-class drift (`nornir_imageregistration`)

**Problem:** Parallel `ControlPointBase` / Landmark / Triangulation (and similar) host+device copies invite asymmetric fixes (epsilon, FlipWarped, Ensure4xN, FindDuplicates).

**Direction:**

- Prefer shared helpers over duplicated methods; keep thin backend-specific shells.
- Rule of thumb already in AGENTS: `xp = cp.get_array_module(input)` for transforms; audit remaining `UsingCupy()` output forcing.
- Add a small “parity checklist” test matrix (same inputs → NumPy vs CuPy) for control-point mutate/dedupe/flip.

**Deliverable:** Short design note + 2–3 parity tests; optional follow-up PR consolidating one dual pair.

### 2. Volume XML dirty / save ownership (`nornir_buildmanager`)

**Problem:** Create-on-read, read-side mutation, Element-as-Iterable `_SaveNodes`, linked vs embedded dirty flags, and generator `findall` confuse when parents persist.

**Direction:**

- Document the contract: who may create children, when getters mutate, when Save walks vs saves the returned node.
- Prefer find-or-empty on getters; create only in setters / `GetOrCreate*`.
- Keep `_SaveNodes` Element special-case; add regression tests for “return block_node” stages.

**Deliverable:** `docs/` or volumemanager README section + expand `test_import_volumedata_save`.

### 3. Pool / process abstraction cleanup (`nornir_pools`)

**Problem:** Immediate vs queued process tasks, ParallelPython callback forever-wait + ActiveJobCount, and telemetry inconsistency caused P0 overnight bugs.

**Direction:**

- Single mental model: every `add_*` returns a Task; shutdown always drains.
- PP: fail-fast or bounded wait instead of infinite hang when callback never fires; always unwind `ActiveJobCount`.
- Clarify which pools are safe for shell commands vs Python callables.

**Deliverable:** Pool API notes in package README; PP wait/timeout change behind tests if cluster available.

### 4. Memory-bounded I/O vs whole-dataset habits

**Problem:** Streaming rules exist in AGENTS, but checksums, assemble paths, and importers still buffer large tiles/files.

**Direction:**

- Inventory hot paths that load full mosaics/volumes; mark accept/reject with thresholds.
- Prefer path/metadata across process boundaries; keep memmap / temp-dir patterns consistent with docker worker layout.

**Deliverable:** Checklist in overnight progress → prioritized tickets (assemble, import, checksum).

### 5. Flip / Flop / mosaic coordinate contract

**Problem:** ImageMagick Flip/Flop, mosaic Write Flip/Flop, idoc Utah Y-invert, and transform FlipWarped were easy to mis-implement (overnight Y-shift bug).

**Direction:**

- One written contract: axes, origin, when Flip means X vs Y, interaction with downsample and mosaic image size.
- Cross-link from mosaicfile Write, idoc import, and transform Flip APIs.

**Deliverable:** `docs/` page or imageregistration README section + one golden fixture test.

## Suggested morning order

1. Skim `.cursor/overnight-bug-review-progress.md` behavioral notes (checksums, GenNameFromDict, STOS rebase, refine fallback).
2. Pick theme **2** or **5** first if shipping volume/align today; otherwise **1** if refining transforms.
3. Do **not** reopen overnight P0s unless a regression test fails — treat them as landed pending CI.

## Out of scope for this plan

- Committing overnight diffs (wait for explicit ask).
- Cross-tool CLAUDE.md / AGENTS single-copy rules (separate plan).
- Full ParallelPython cluster validation without a live PP environment.
