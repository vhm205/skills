---
name: test-driven-development
description: "Applies test-first development when required by the adapter, task or user, or selected for a regression fix. Optional otherwise; debugging owns root-cause investigation."
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

## The cycle

1. **RED.** Write one small test for one behavior, with a name that says what breaks. Use real
   code. Mock only what you cannot run (network, clock, third parties).
2. **Verify RED (do not skip).** Run it. It must *fail*, not error, and fail because the
   behavior is missing. If it passes, it tests existing behavior: rewrite it.
3. **GREEN.** Write the minimum code to pass. No speculative features.
4. **Verify GREEN.** Run the test and the adapter's test suite. Output should be clean. Name
   any failure, even one you didn't cause.
5. **REFACTOR.** Only while green. Re-run after each refactor.

## Rules in a `tdd: required` project

- Production code written before its test: delete it and redo it test-first. Don't keep it
  "as reference".
- A test written after the code proves nothing until you have seen it fail. Break the code
  temporarily to confirm it can.

## Good tests

- Test behavior through the public interface, not private details.
- One reason to fail per test.
- Ask "would this test fail if the feature broke?" If not, it is decoration.

_Adapted from `test-driven-development` of obra/superpowers (MIT, © 2025 Jesse Vincent), relaxed from mandatory to
adapter-controlled. License in the kit's `NOTICE.md`._
