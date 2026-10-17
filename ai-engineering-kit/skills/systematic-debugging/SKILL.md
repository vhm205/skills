---
name: systematic-debugging
description: "Investigates bugs, failing checks or unexpected behavior when the cause is not yet proven, before attempting a fix."
---

# Systematic Debugging

**Iron rule: no fix without a root cause investigation first.** Symptom patches create new bugs.

## Phase 1: Root cause

1. **Read the error completely**: full message, stack trace, line numbers, logs.
2. **Reproduce reliably.** Write down the exact steps or a failing test. If it does not
   reproduce, gather more data (logs, inputs, environment). Do not guess.
3. **Check what changed**: `git log`, `git diff`, dependency or config changes, environment.
4. **Multi-component systems:** instrument each boundary (what enters, what leaves) and run
   once to find *where* it breaks before asking *why*.
5. **Trace backward** from the bad value to where it originates. Fix at the source, not where
   it surfaced. See `references/root-cause-tracing.md`.

## Phase 2: Pattern

Find similar code that works. Read it fully. List every difference between working and
broken, however small. Check assumptions about dependencies and configuration.

## Phase 3: Hypothesis

State it in writing: "I think X is the root cause because Y." Test it with the smallest
possible change, one variable at a time. If it is wrong, form a new hypothesis. Do not stack
another fix on top. If you don't understand something, say "I don't understand X" and go find out.

## Phase 4: Fix

1. Capture the bug in a failing test (or a scripted reproduction if a test is impractical).
2. Make one fix aimed at the root cause.
3. Run `verifying-change`: the reproduction passes, nothing else broke.

## Three strikes rule

If **three** fix attempts have failed, stop. Repeated failures that each reveal a new problem
in a different place mean the architecture or your understanding is wrong, not the last fix.
Report **BLOCKED** (or **NEEDS DECISION** if a redesign is the real question) per
`.aiek/core/handoffs.md`, listing the hypotheses tried and the evidence for each.

## If the fix changes intended behavior

A root cause that requires changing what the system is *supposed* to do is no longer a bug fix.
Re-classify (`.aiek/core/classification.md`). Normal/Large fixes go through Spec Kit.

## Red flags

"Quick fix for now", "just try changing X", "one more attempt", adding retries or longer
timeouts without knowing why, proposing a fix before you can explain the failure.

_Adapted from `systematic-debugging` of obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
