---
name: verifying-change
description: "Use when a change is about to be claimed done, fixed, passing or ready to merge, or when asked to 'run the tests', 'prove it', 'is it done?', 'verify this'. Runs the checks that match the claim and the changed scope - fast targeted checks first, then the full gate - plus lint, typecheck, build, e2e or observed system state, compares the result against the project baseline, and returns the evidence table for DONE. Not for reviewing code or diffs (use reviewing-change), release acceptance and sign-off (use accepting-change), or investigating a failure whose cause is not proven (use systematic-debugging)."
---

# Verifying a Change

**Iron rule: no completion claim without fresh verification evidence.**
If you did not run the check in this session after the last edit affecting its scope, you
cannot say it passes.

## What counts as passing

If the adapter names `baselines` (or the v1 `baseline` alias), passing means **no failures
beyond the listed baseline**, not zero failures. Read the named baseline, say in the evidence
which failures you matched against it, and treat anything outside it as a regression — however
unrelated it looks. Never widen the baseline to absorb a new failure, and never weaken a check
to reach green.

Where behavior cannot be expressed as a test — infrastructure, deployment, capacity — observed
system state and measured thresholds are valid evidence, on the same terms: a command, its real
output, and what it proves. See `shipping-infrastructure`.

## The gate

1. **Identify** which commands prove the claim. Take them from the adapter: `verify.test_fast`
   for quick iteration, `verify.test_full` for the final gate, plus `verify.lint`,
   `verify.typecheck`, `verify.build`, `verify.e2e` and any check a task or acceptance criterion
   names. The final gate is the full selection, not the fast one.
2. **Run** the relevant checks after the last change affecting their scope. Reuse evidence
   for unchanged state and scope as defined in `.aiek/core/WORKFLOW.md`.
3. **Read** the output: exit code, failure count, warnings that matter. Not just the last line.
4. **Compare** against the claim. Does the evidence actually show it?
5. **Only then** state the result, quoting the evidence.

## Optional helper script

If the kit installed `.aiek/scripts/verify.py`, it runs this gate and writes the evidence:

```bash
python .aiek/scripts/verify.py --adapter .aiek/adapter.md --scope changed --only test,lint --json --dry-run
```

Drop `--dry-run` to run. It prints each command before executing it, records exit codes and
output, and compares failures against the adapter's baseline. `--scope changed` is the fast pass;
`--scope all` is the full gate. The script is optional: when it is absent, cannot parse the
adapter, or the claim needs a check it does not model, run the same commands by hand. A dry-run
plan is not evidence; only executed commands and their real output count.

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

## Gotchas

- A run from before the last edit to shared code is stale even if the command is unchanged.
- A mocked unit test proves the mock, not the integration behavior the claim is about.
- Matching a failure to the baseline without naming the entry can hide a different failure.
- Dry-run output and a script's exit code are not executed evidence.
- Reusing the pre-review-fix run after the fixes, because the command did not change.

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
