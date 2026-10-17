---
name: verifying-change
description: "Checks evidence when claiming a change is fixed, passing or complete, and before integration. Uses checks relevant to the claim and changed scope."
---

# Verifying a Change

**Iron rule: no completion claim without fresh verification evidence.**
If you did not run the check in this session after the last edit affecting its scope, you
cannot say it passes.

## The gate

1. **Identify** which commands prove the claim. Take them from the adapter
   (`verify.test`, `verify.lint`, `verify.typecheck`, `verify.build`, `verify.e2e`), plus any
   check a task or acceptance criterion names.
2. **Run** the relevant checks after the last change affecting their scope. Reuse evidence
   for unchanged state and scope as defined in `.aiek/core/WORKFLOW.md`.
3. **Read** the output: exit code, failure count, warnings that matter. Not just the last line.
4. **Compare** against the claim. Does the evidence actually show it?
5. **Only then** state the result, quoting the evidence.

## What each claim needs

| Claim | Evidence required |
|---|---|
| Tests pass | test run output with 0 failures (name any pre-existing failures from the baseline) |
| Build / typecheck OK | exit 0 from the build or typecheck command (a passing linter is not a build) |
| Bug fixed | the original reproduction now behaves correctly |
| Regression test added | it fails without the fix and passes with it (check both) |
| Acceptance criteria met | each criterion from spec.md checked one by one, with how |
| Subagent finished its task | the actual diff inspected and checks re-run; not its report |
| UI change works | the adapter's run/preview step, observed, or say it was not observed |

## When you cannot verify something

Say so explicitly in DONE under **Remaining risks**: what was not verified, why, and what
would verify it. Never paper over it.

## Red-flag words

If you are about to write "should work", "probably", "seems to", "looks good", "Done!",
"Perfect!" without evidence in the same message: stop and run the gate.

## Output

A short evidence table that goes straight into the DONE report:

| Check | Command | Result |
|---|---|---|
| tests | `<cmd>` | `<N passed, 0 failed>` |
| typecheck | `<cmd>` | exit 0 |
| AC-1 "<criterion>" | `<how checked>` | confirmed |

_Adapted from `verification-before-completion` of obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
