---
name: systematic-debugging
description: "Investigates bugs, failing checks or unexpected behavior when the cause is not yet proven, before attempting a fix. Covers intake of the report, tracing the cause, fixing at the source, confirming the fix is actually running, and registering the reproduction as a permanent regression."
---

# Systematic Debugging

**Iron rule: no fix without a root cause investigation first.** Symptom patches create new bugs.

## Phase 0: Intake

You cannot investigate a report you do not have. Before anything else, check you know:

| | |
|---|---|
| **When** it was seen | enough to line up logs and traces |
| **Where** | which environment and build; several similar environments usually run different code |
| **How to get there** | the exact location, url or entry point |
| **The steps** | with **the real data that was entered**, not a description of it |
| **What happened** | verbatim error text or payload, not a paraphrase |
| **What was expected** | stated as an observation, because this becomes the test's assertion |
| **Severity and frequency** | always, or one time in five — an intermittent bug needs a different strategy |
| **Evidence** | a trace id, a log excerpt, an image, a conversation or request id |

Missing pieces: **ask**. Do not fill them in by guessing, and do not start reproducing against
an environment nobody named. The adapter may point at the project's own report format.

## Phase 1: Root cause

1. **Trace first if the system is traced.** When the report carries a trace, request or
   conversation id, read that record of the failing run *before* trying to reproduce. It is the
   cheapest evidence you will get. The adapter names how to fetch one and which specialized
   investigation to route to for a given surface.
2. **Read the error completely**: full message, stack trace, line numbers, logs.
3. **Reproduce reliably.** Write down the exact steps or a failing test. If it does not
   reproduce, gather more data. Do not guess.
4. **Check what changed**: `git log`, `git diff`, dependency or config changes, environment.
5. **Multi-component systems:** instrument each boundary (what enters, what leaves) and run once
   to find *where* it breaks before asking *why*.
6. **Trace backward** from the bad value to where it originates. Fix at the source, not where it
   surfaced. See `references/root-cause-tracing.md`, which also lists the failure families that
   produce no error at all.

## Phase 2: Pattern

Find similar code that works. Read it fully. List every difference between working and broken,
however small. Check assumptions about dependencies and configuration.

## Phase 3: Hypothesis

State it in writing: "I think X is the root cause because Y." Test it with the smallest possible
change, one variable at a time. If it is wrong, form a new hypothesis. Do not stack another fix
on top. If you don't understand something, say "I don't understand X" and go find out.

## Phase 4: Fix

1. Capture the bug in a failing test (or a scripted reproduction if a test is impractical),
   at the lowest layer that can prove the behavior.
2. Make one fix aimed at the root cause.
3. Run `verifying-change`: the reproduction passes, nothing else broke.

## Phase 5: Confirm the fix is actually running

A patch that exists in the repository is not a patch that is running. Before claiming anything:

- **Was the process restarted or rebuilt?** A bind-mounted file is not a reloaded module.
- **Do not check by starting a new process.** A fresh process loads the new code whatever the
  serving process is running, so it always agrees with you. Compare the running instance's
  start time against the file's timestamp instead.
- **Were the other artifacts refreshed?** An environment is the application *plus* its side
  services, its data, its cached assets and its generated indexes. Each is updated separately.
- **Was the migration applied, the cached asset version bumped, the index rebuilt?**
- **Is this the environment the report named?**

The adapter lists the project's specific commands and traps for each of these.

## Phase 6: Register the regression

The reproduction only protects you if the gate actually runs it.

- Put the test where the project's gating lane picks it up. If that lane uses an explicit list
  of files rather than a directory, **add the file to the list** — otherwise the gate stays
  green without ever running it.
- Follow the project's naming convention so the test stays traceable to the report.
- Then confirm it: the gate run must show the new test, not just a green total.

## Three strikes rule

If **three** fix attempts have failed, stop. Repeated failures that each reveal a new problem in
a different place mean the architecture or your understanding is wrong, not the last fix.
Report **BLOCKED** (or **NEEDS DECISION** if a redesign is the real question) per
`.aiek/core/handoffs.md`, listing the hypotheses tried and the evidence for each.

## If the fix changes intended behavior

A root cause that requires changing what the system is *supposed* to do is no longer a bug fix.
Re-classify (`.aiek/core/classification.md`). Normal/Large fixes go through Spec Kit.

## Red flags

"Quick fix for now", "just try changing X", "one more attempt", adding retries or longer
timeouts without knowing why, proposing a fix before you can explain the failure, declaring a
fix verified without checking it is the code that ran.

_Adapted from `systematic-debugging` of obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
