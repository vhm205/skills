---
name: test-driven-development
description: "Applies test-first development when required by the adapter, task or user, or selected for a regression fix. Covers choosing the layer that can actually prove the behavior, proving the test can fail, and keeping the red/green record as evidence. Optional otherwise; debugging owns root-cause investigation."
---

# Test-Driven Development (optional)

Write the test first, watch it fail for the right reason, then write the least code that makes
it pass.

## When it applies

- **Required** when the adapter sets `tdd: required` (globally or for listed paths), or a task
  says so.
- **Recommended** for bug fixes (the failing test *is* the reproduction) and for logic-heavy code.
- **Usually skip** for config, copy, generated code, throwaway spikes, and pure wiring. In a
  `tdd: required` project, skipping needs the person's OK. Record it as a ruling.
- **Not applicable** when the behavior cannot be expressed as a test at all — infrastructure,
  deployment, capacity. Use `shipping-infrastructure`, which keeps the same discipline with a
  measured threshold in place of a failing test.

## Choose the layer first

Write the test at the **lowest layer that can actually prove the behavior**. The adapter lists
the project's layers and where each one lives; prefer the cheapest one that would fail if the
feature broke.

- Pure logic — validators, parsers, resolvers, formatting — belongs at the unit layer.
- Anything whose correctness depends on a real dependency parsing it (a query, a schema, a
  template) needs a test against that real dependency. A fake one proves only that you built a
  string.
- Reach for a browser or end-to-end test only for behavior that exists only there.

A **sentinel** test — one that greps the source for a string rather than running it — is the
weakest form. Use it only when no layer can run the behavior, say so, and replace it with a
behavioral test when one becomes possible.

## The cycle

1. **RED.** Write one small test for one behavior, with a name that says what breaks. Use real
   code. Mock only what you cannot run (network, clock, third parties).
2. **Verify RED (do not skip).** Run it. It must *fail*, not error, and fail because the
   behavior is missing. If it passes, it tests existing behavior: rewrite it.
3. **GREEN.** Write the minimum code to pass. No speculative features.
4. **Verify GREEN.** Run the test and the adapter's test suite. Name any failure, even one you
   didn't cause.
5. **REFACTOR.** Only while green. Re-run after each refactor.

## Keep the red/green record

The two runs are evidence, not ceremony. For each behavior, keep:

| | |
|---|---|
| RED | the command, the exit code, and the **failure line verbatim** |
| GREEN | the same command, the exit code, and the result |

`authoring-pr` puts this record in the description; a reviewer reads it to see the test can
actually fail. A test with no recorded red state is indistinguishable from one that asserts
nothing.

## Prove the test is not empty

If the code was written before the test — which happens — the test has never been observed
failing, so it proves nothing yet. **Unwire the fix, re-run, and watch it go red**, then put the
fix back. In a `tdd: required` project the stricter rule applies: delete the production code and
redo it test-first, rather than keeping it "as reference".

## What "green" means

If the adapter names a `baseline` of known failures, green means **no failures beyond that
baseline** — not zero failures. A failure outside the baseline is a regression, however
unrelated it looks.

**Never weaken an assertion to reach green.** Narrowing a check, loosening a comparison, or
marking a test skipped to clear a run destroys the only thing the test was for. If a test is
wrong, fix it deliberately and say so.

## Good tests

- Test behavior through the public interface, not private details.
- One reason to fail per test.
- Ask "would this test fail if the feature broke?" If not, it is decoration.
- Be suspicious of a test that mirrors the implementation — copying the same list into both
  sides proves the copy, not the behavior.

_Adapted from `test-driven-development` of obra/superpowers (MIT, © 2025 Jesse Vincent), relaxed from mandatory to
adapter-controlled. License in the kit's `NOTICE.md`._
