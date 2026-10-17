---
description: "Run the verifying-change gate and produce an evidence table for the DONE report"
---

## User Input

```text
$ARGUMENTS
```

## Goal

Produce fresh verification evidence for the implemented feature. Nothing may be called done
without it.

## Steps

1. Load and follow the `verifying-change` skill (installed by the AI Engineering Kit). If the
   skill is not available, apply its rule directly: identify the checks, run them fresh, read
   the full output, and claim only what the output shows.
2. Commands come from `.aiek/adapter.md` (`verify.*`). Resolve `auto` or missing values with
   `.aiek/core/command-discovery.md`.
3. Check every acceptance criterion in the active feature's `spec.md` one by one and record
   how each was confirmed. Confirm all tasks in `tasks.md` are ticked; list any that are not.
4. Output the evidence table:

   ```markdown
   ## Verification
   | Check | Command / method | Result |
   |---|---|---|
   ```

   followed by **Not verified:** (what, why, what would verify it), or "nothing".
5. If a check fails: do not continue to review. Fix it through the `executing-task` /
   `systematic-debugging` skills, then re-run this command. After three failed fix attempts,
   report BLOCKED per `.aiek/core/handoffs.md`.
