---
name: hypothesis-testing
description: >-
  Guides pytest unit tests toward Hypothesis property-based testing when inputs
  are variable, structured, combinatorial, or numerical; pairs property tests
  with explicit examples for regressions and known edges. Use when writing or
  reviewing tests, serialization or round-trips, ndarray or numerical code, or
  when deciding between @given and parametrization. 
---

# Hypothesis testing

## When to use Hypothesis

- Use **`@given` and strategies** when inputs are **high-dimensional**, **combinatorial**, **structured** (nested dicts, trees, records), or **hard to enumerate** without missing cases.
- Use Hypothesis for **data structures** when **invariants**, **round-trips** (encode/decode, serialize/parse), or **validity constraints** matter more than a fixed list of instances.
- Prefer **plain `pytest.mark.parametrize` (or a tiny hand-written table)** when there are **few discrete cases** and properties would add noise or slow CI without meaningful coverage.

## Mathematical and numerical code

- Prefer Hypothesis when behavior depends on **ranges of reals**, **several coupled parameters**, **array shape or dtype**, or **known identities** (algebraic or analytic properties you can assert as properties).
- Combine property checks with **tolerance-based** assertions where appropriate; restrict strategies to the function’s **domain** (e.g. positive arguments where required) and control **`allow_nan` / `allow_infinity`** to match defined behavior.
- Use **`hypothesis.extra.numpy`** for **array strategies** when testing vectorized or ndarray code; constrain **shape**, **dtype**, and value ranges so tests stay fast and failures are interpretable.
- Keep **`@example`** or small **parametrize** blocks for **canonical** scalars (0, 1, -1, small integers, π where relevant), **documented** numerical edge cases, and regressions.

## Pairing with explicit examples

- Keep a **small** set of **`@example(...)`** and/or **`@pytest.mark.parametrize`** for **documented regressions**, **known edge cases**, and **API contracts** you want visible in the test body.
- Do not duplicate the same scenario in both Hypothesis and parametrization unless one documents intent and the other explores the space (avoid redundant maintenance).

## Engineering hygiene

- Tune **`settings`**: `max_examples`, `deadline`; use **`suppress_health_check`** only with a **short comment** explaining why (e.g. unavoidable heavy setup).
- Rely on **shrinking** for minimal failures; mention **reproducibility** when it matters: **`@reproduce_failure`**, **Hypothesis example database** / CI artifacts for flaky failures.

## Anti-patterns

- Over-broad strategies that make tests slow or flaky without tightening invariants.
- Property tests with no clear **property** or **oracle** (only random smoke).
