---
name: accepting-change
description: "Runs the acceptance pass after automated checks are green: re-runs the full scenario suite, builds the acceptance sheet for whatever only a person can confirm, and collects sign-off. Has a product mode for user-facing behavior and an ops mode for infrastructure and deployment work. Use before release or hand-off, not as a substitute for verification."
---

# Accepting a Change

Verification proves the code does what the code was meant to do. Acceptance proves **the person
on the other end gets what they were promised** — and records who said so.

Run this after `verifying-change` is green, before release or hand-off.

## Pick the mode

| Mode | When | Evidence |
|---|---|---|
| **product** | User-facing behavior changed | Scenario suite re-run + acceptance sheet signed by a person |
| **ops** | Infrastructure, pipeline, deployment or release process changed | Post-change smoke, before/after comparison, rehearsed rollback |

A change can need both. Run product first, then ops.

## The reporting rule, in both modes

**A step the machine could not run is reported SKIPPED with its reason. It never counts as
passed.** Skipped steps fall through to the person-checked part; they do not disappear.

**Do not create a second summary.** If the project has a report page, the numbers go there.
One place, or reviewers compare two pages and trust the friendlier one.

---

## Product mode

### 1. Re-run the full scenario suite

Run the adapter's `verify.uat` command. This is a different question from the test suite: the
suite proves the functions are right, this proves the journey is right.

Read the report it produces. Record the run as it happened — passes, failures, skips, and the
reason for each skip.

### 2. Build the acceptance sheet

Source: the traceability table from `intaking-ticket`. Every row in the **person-checkable**
bucket becomes a case; every **machine-checkable** row that the suite skipped becomes a case
too.

Order the sheet so it can be stopped early and still be useful:

1. **Smoke** — the few cases that would make everything else pointless if they failed.
2. **Full** — the rest, grouped by area.
3. **Regression** — what must still work and is easy to break from here.

Use `references/uat-sheet-template.md`. Each case states the steps, **the real data to enter**,
the expected observation, and leaves room for the result and the signature.

### 3. Collect sign-off

A case nobody could check is written as "not checked — reason", never left blank and never
marked passed. The sheet is done when every case has a result and the approver has signed.

---

## Ops mode

Use `references/ops-acceptance-template.md`. Three parts, in order:

1. **Post-change smoke.** The services are up, the health checks answer, the thing that was
   changed is observably in the state you intended — confirmed by looking at the running
   system, not by the fact that a command exited zero.
2. **Before / after comparison.** The numbers or states you recorded before the change, beside
   the ones after it. Unchanged things should be unchanged; name anything that moved and
   whether you expected it.
3. **Rollback rehearsal.** For anything hard to reverse, the rollback was *performed* in an
   isolated environment and its output recorded. A rollback plan that was never run is a plan,
   not evidence.

Ops acceptance is not complete while any of the three is missing. Say which one is missing
rather than declaring the change accepted.

---

## Exit

Report per `.aiek/core/handoffs.md`:

- **DONE** when every case has a result and the required sign-off exists.
- **BLOCKED** when a case cannot be checked and the change cannot ship without it.

The report names the number of cases passed, failed, skipped and not checked, and links to the
sheet. Do not summarize a mixed result as a pass.

## Red flags

- A skipped machine step counted in the pass column
- An acceptance sheet with blank result cells, declared complete
- A second summary page created "for convenience"
- A rollback section describing what would be done
- Sign-off recorded by the person who wrote the change, when the project requires someone else
