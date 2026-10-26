---
name: nornir-review-issue-fixing
description: >-
  End-to-end procedure for fixing a Nornir code-review finding: treat the issue text as an
  unproven hypothesis, reproduce or measure before editing, write a test that fails against the
  old code, commit in the submodule then bump the umbrella pointer, close the issue with
  evidence, and update the master list. Use when working `.cursor/nornir-bug-review-master.md`,
  a `jamesra/nornir-review` issue, a static-analysis finding, or any queue of "fix one issue at
  a time" work in this monorepo.
---

# Fixing a Nornir review finding

Paired rule (the non-negotiable core): [`.cursor/rules/Review-driven-bugfixing.mdc`](../../rules/Review-driven-bugfixing.mdc).

Findings in [`.cursor/nornir-bug-review-master.md`](../../nornir-bug-review-master.md) and the
`jamesra/nornir-review` tracker came from reading code. Most are correct, several are half right in
ways that matter, a few are wrong. The expensive mistakes all came from trusting the finding's
explanation instead of its symptom.

## Loop

1. **Pick** the highest-severity open item (P0 → P3). Cross-check master-list `Status` against the
   tracker; they drift.
2. **Reproduce or measure** before any edit (*Verify before fixing*).
3. **Fix** the cause you measured, not the one the finding named if they differ.
4. **Test** so the new test fails against the old code (*Tests*).
5. **Verify** the surrounding suites, separating pre-existing failures from yours.
6. **Commit** in the submodule, then bump the umbrella pointer.
7. **Close** the issue with a comment carrying the numbers; set the master-list `Status`.
8. **Record** any durable lesson in the matching skill *in the same commit*.
9. **File** anything found on the way as a separate issue; do not fold it in.

## Verify before fixing

- **Execute the failing path.** If it cannot be reproduced here, say so and treat it as unproven.
  A locale-dependent read (`open(f, 'r')` labelled `utf-8`) is invisible on a UTF-8 host.
- **Follow the observation that contradicts the theory**: it usually means the wrong theory, not an
  outlier. In #245, filed plausibly as mojibake, `'t' != 'K'` (no codec maps those to each other)
  exposed the real cause: Hypothesis examples leaking through a shared `setUp`.
- **Measure the layer you change in isolation.** When two allocations overlap, the larger transient
  hides the smaller, so fixing the hidden one first measures as *no improvement*. In #157 the
  requested zero-copy caller rewrite saved nothing until `array.fromfile`'s own 2.06x reallocation
  underneath was fixed; both layers had to change.
- **Establish the noise floor first**: fix the configuration, vary only the seed. `ScoreOneAngle` is
  stochastic (#95); the coarse-grid peak deltas in #234 sat inside the seed spread of the
  *unchanged* code, so they were not decimation error.
- **Test the boundary, not just the reported condition.** #236 was filed as a `budget_bytes <= 0`
  branch; writing the fix as a floor exposed a second silent collapse at 1281 MiB free, *above* the
  reported cliff, where the ordinary path floor-divided to zero.

## Tests

- The test must **fail against the previous behaviour**. Verify: `git -C <repo> worktree add --detach <scratch> HEAD`,
  copy the new test in, run it there (never `git stash`). Quote the count ("9 of the 12 fail against
  the previous behaviour"); a test that passes both ways is documentation, not a regression guard.
- **Check a timing-bug test for the same timing bug.** A `getmtime` float does not round-trip
  through `os.utime`; that test passed intermittently against unfixed code. Use nanoseconds.
- `unittest.setUp` runs **once per test method** while `@given` runs many examples inside it, so all
  Hypothesis examples share that fixture; shared directories, channels and files produce failures
  that read as corruption. See [hypothesis-testing](../hypothesis-testing/SKILL.md).
- Assert the **property**, not a value: #236's central test sweeps free VRAM and asserts no adjacent
  level drops the chunk by more than 4x. Value assertions go stale (two in `test_refine_shared.py`
  had been failing unnoticed since #228).
- Assert **both directions** when the premise could evaporate (that the old pattern really did cost
  an extra copy), so the test fails loudly instead of quietly asserting something free.
- Make fakes faithful to the real return type: a `_TagData` exposing only `tobytes()` cannot
  represent data read through the buffer protocol.

## Your failures vs the repo's

- **Re-run on a `HEAD` worktree** before blaming a diff (shared checkout; never stash).
  Current known failures: the table in [nornir-verify-change](../nornir-verify-change/SKILL.md)
  (`tests/transforms`, once 18 failures, passed in full 2026-10-26; `TestBasicTileAlignment` still
  rotates one or two per combined run with and without local changes).
- Compare **failure sets across repeats**, not one combined run.
- A byte-identical error value against an earlier record (e.g. `1085.9270565544502` for #235) is a
  known failure.
- [nornir-headless-unit-tests](../nornir-headless-unit-tests/SKILL.md): `NORNIR_HEADLESS` and the
  import-time `matplotlib.use` trap that wedges whole sessions.

## Performance claims

- Give **before/after numbers** with the configuration (size, dtype, repeats, median vs mean).
- **State the cost of work you added**, even when small (~40µs per call against ~350µs, ~40ms per
  thousand-section volume). Do not call it free.
- Keep an existing cheap guard that protects an expensive path. #245 kept the mtime check for image
  pyramids and added content comparison only for small notes files; replacing it globally looked
  tidier and was wrong.
- Make a speedup **opt-in** when its accuracy is established on one pair, and say what default-on
  still needs.
- If a sign-off rule's rig does not apply (`stos_brute` is slice-to-slice and consumes no tiles, so
  the ≥100-tile rule cannot apply), **flag that** instead of claiming a sign-off you did not run.

## Scope

- File side findings **separately**, especially when the fix needs a decision rather than being
  mechanical (which encoding fallback; whether the ROI path's analogous collapse transfers).
- Do not ride a behaviour change along inside an unrelated fix.
- Prefer **warn over raise** when the degraded run still produces correct results and the defect was
  silence; throttle the warning on hot calls.

## Landing the change

Commit in the submodule, then bump the umbrella pointer per
[`.cursor/rules/Monorepo-submodule-changes.mdc`](../../rules/Monorepo-submodule-changes.mdc)
(message: `Update nornir-buildmanager: recopy notes on content change, not mtime alone (#245)`). Then:

- Close the tracker issue with the measurements, test names and counts, and **an explicit
  correction when the finding's diagnosis was wrong** (what a future master-list reader needs most).
- Set `Status` (and the `Issue` link) in `.cursor/nornir-bug-review-master.md`.
- Working notes go under `.cursor/issue-handoff/`, not the repository root.
