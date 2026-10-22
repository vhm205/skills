---
name: shipping-infrastructure
description: "Carries out infrastructure, build-pipeline, deployment, release-process and capacity work, where the proof of correctness is an observed system state or a measured threshold rather than a failing test. Records the architecture decision, collects ops evidence, and rehearses rollback before anything irreversible. Use for this class of change instead of the ordinary execution path."
---

# Shipping Infrastructure

Infrastructure work fails differently from product work: nothing goes red, the command exits
zero, and the system is still wrong. This skill replaces "write a failing test" with **evidence
that the running system is in the state you intended**.

## Scope

Use this for changes to: infrastructure and topology, build and image pipelines, deployment and
release process, configuration and secrets plumbing, and capacity or performance work whose
acceptance is a threshold.

**This work is always Large.** `.aiek/core/classification.md` already makes it a hard trigger;
do not score it down because the diff is small. A three-line pipeline change can take
production down.

## Step 1: record the decision before building

If there was a real fork — where to run a component, which platform, what the cutover order is
— it was decided by a human (via `exploring-idea` ending in NEEDS DECISION). Record it in the
Spec Kit `plan.md` as a decision entry:

> **Decision:** <what was chosen>
> **Real constraints:** <what the system actually requires — protocol, network mode, hardware,
> data locality — discovered, not assumed>
> **Rejected:** <option, and the specific reason>
> **Irreversible once done:** <what>
> **Cost if wrong:** <what it takes to undo>

One place only. Do not open a separate decision document; `.aiek/core/WORKFLOW.md` keeps the
Spec Kit artifacts as the single plan.

If no decision was recorded and the fork is real, stop and get it decided first.

## Step 2: state the evidence before you start

Decide **what will prove this worked**, and write it down before the work, the same way a test
is written before the fix. `references/ops-evidence-sheet.md` has the table.

| Change | What proves it |
|---|---|
| Build / image | The published artifact's identity equals the source revision it claims; the identity variable was actually passed in, not defaulted |
| Deploy | The project's deploy check passes **and** the running artifact is the new one |
| Configuration | The key is read where you think it is read; name the key, never the value |
| Capacity / performance | The measurement was run **before** and did not meet the threshold, and meets it after |
| Irreversible change | A rollback was performed in an isolated environment and its output captured |

For capacity work this restores the red/green cycle with a different unit: **measure first and
see it fail the threshold**, then change, then measure again. A threshold only met after the
fact, never observed failing, proves nothing — exactly as an untested test does.

## Step 3: do the work, in reversible order

- Build and verify the artifact before anything consumes it.
- Change the lowest-risk environment first and accept it there before the next one.
- Keep each step separately revertible; a step that cannot be undone goes last, after its
  rollback has been rehearsed.
- Feature-gate behavior changes off by default when the change can be landed dark.

## Step 4: prove it is live

The failure that costs the most is a change that was applied to the repository and never
reached the running system.

- "The command exited zero" is not evidence. Look at the system.
- **Do not verify by starting a new process.** A fresh process loads the new code regardless of
  what the serving process is running, so it always agrees with you. Compare the running
  instance's start time against the artifact's timestamp, or compare artifact identities.
- An environment is several independent artifacts — the application, its side services, its
  data, its generated indexes. Patching one does not refresh the others; name each one you
  touched and check each one.
- A change does not retroactively fix artifacts already published to someone else. Ask which
  ones already went out and whether they are affected.

## Step 5: hand to acceptance

Run `accepting-change` in **ops** mode: post-change smoke, before/after comparison, rollback
rehearsal. Then report per `.aiek/core/handoffs.md`.

## Hard rules

- **Ask before anything irreversible or outward-facing**: publishing an artifact others
  consume, cutting over an environment, deleting data, changing a shared pipeline. Prior
  approval for one step is not approval for the next.
- **Nothing is done until rollback has been rehearsed**, for anything hard to reverse.
- **Never put a secret value in a file, a description or a report.** Names only.
- **Record what you could not verify**, by name. An unverified step reported as done is the
  failure mode this whole skill exists to prevent.

## Red flags

- "Deployed successfully" with no observation of the running system
- A threshold reported as met with no before-measurement
- A rollback section written in the conditional tense
- Treating a small diff as a small change
- Verifying a running service by invoking a new one
