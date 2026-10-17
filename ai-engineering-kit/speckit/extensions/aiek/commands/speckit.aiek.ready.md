---
description: "READY TO BUILD gate: check spec, plan and tasks are complete and consistent before implement"
---

## User Input

```text
$ARGUMENTS
```

## Goal

Decide whether the active feature is **READY TO BUILD**. This gate is read-only: it reports,
it does not rewrite the artifacts. (For a deep cross-artifact analysis use
`__SPECKIT_COMMAND_ANALYZE__`; this gate is the quick go/no-go.)

## Steps

1. Use the installed upstream prerequisite helper from the project root:
   `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`, or
   `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`.
   Read the returned `FEATURE_DIR`'s `spec.md`, `plan.md`, `tasks.md`. On failure or ambiguity,
   report BLOCKED; never guess from modification times or select the newest feature directory.
2. Check each item and record pass/fail with a one-line reason:
   - [ ] spec.md has no unresolved `[NEEDS CLARIFICATION]` markers
   - [ ] every user story has acceptance criteria / scenarios that can be checked
   - [ ] plan.md exists and its Constitution Check (if any) has no unjustified violations
   - [ ] tasks.md covers every user story (map story numbers/headings to `[USn]` tasks)
   - [ ] code tasks name concrete paths; non-code tasks name a concrete artifact or check
   - [ ] `[P]` markers are plausible: no two `[P]` tasks in the same phase edit the same file
         (see `.aiek/core/parallelism.md`)
   - [ ] each phase checkpoint says how it will be verified (a test, command, or manual check);
         commands can come from `.aiek/adapter.md`
   - [ ] no open product/architecture trade-off is left for the implementer to decide
3. Read the lane from plan.md and re-check `.aiek/core/classification.md` against current
   scope. Before implementation of Large work, run `__SPECKIT_COMMAND_ANALYZE__` (or reuse
   analysis for unchanged artifacts) and resolve blocking findings. An after-tasks readiness
   report is not permission to skip this check.
4. Output one of:

   ```markdown
   READY TO BUILD: <feature dir>
   Lane: <NORMAL | LARGE>  ·  Tasks: <n> (<p> marked [P])
   Notes: <anything the implementer should know>
   Next: __SPECKIT_COMMAND_IMPLEMENT__
   ```

   or, if any check fails, a **BLOCKED** or **NEEDS DECISION** report in the format of
   `.aiek/core/handoffs.md`, naming the failing checks and the Spec Kit command that fixes each
   (`__SPECKIT_COMMAND_CLARIFY__`, `__SPECKIT_COMMAND_PLAN__`, `__SPECKIT_COMMAND_TASKS__`).
5. Stop.
