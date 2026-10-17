---
name: executing-task
description: "Applies execution discipline when implementing an authorized Small change or ready tasks from the canonical planning artifacts. Excludes discovery and plan authoring."
---

# Executing a Task

Implement exactly what the source of truth asks for, prove it works, and leave a record.

## Source of truth

| Lane | Read before coding | You may not |
|---|---|---|
| Small | the request itself, plus the adapter | invent extra scope |
| Normal / Large | `specs/<feature>/spec.md`, `plan.md`, `tasks.md` (and `contracts/`, `data-model.md` when the task touches them) | write your own plan, re-order phases, or silently skip tasks |

If no tasks.md exists for Normal/Large work, stop: the change is not READY TO BUILD.
Go back to Spec Kit `tasks`.

## Before the first task

1. Load the adapter (`.aiek/adapter.md`) for commands, conventions and risk areas.
2. Apply the isolation policy in `.aiek/core/WORKFLOW.md` using `using-worktrees` when needed.
3. Run relevant baseline checks once; reuse an unchanged isolation baseline if already run.
4. If the adapter or the task requires TDD, load `test-driven-development`.

## The task loop

Follow completion ownership in `.aiek/core/WORKFLOW.md`. Inside an upstream implementation
command, apply these steps within its existing loop; do not start a second task loop.
For each task, in tasks.md order (or the single Small change):

1. **Read the task** and the spec/plan sections it points to. Restate its done-condition
   in one line.
2. **Check `[P]` neighbours.** If several unfinished tasks are marked `[P]`, hand the
   decision to `parallel-development`. Otherwise continue sequentially.
3. **Implement the smallest change** that meets the task. Match the surrounding code style.
   No "while I'm here" edits.
4. **Run the task's checks** (its test, or the adapter's targeted test command). If something
   fails and the cause is not obvious, switch to `systematic-debugging`. Do not guess-fix.
5. **Mark progress.** Tick the task in tasks.md (`- [ ]` → `- [x]`). Commit if the adapter's
   commit policy says per-task commits.
6. **Record rulings** (see below) before moving on.

## Rulings, not stalls

When the artifacts are silent or slightly wrong, decide and keep going if the call is
reversible and local. Record it as:

`Ruling: <what you decided> — <why> — <cost if wrong>`

Where: Normal/Large → append to `specs/<feature>/execution-log.md` (a log, never a plan).
Small → the DONE report.

**Do not rule. Hand off instead** (`.aiek/core/handoffs.md`) when:

- the change would contradict the spec's requirements or acceptance criteria → fix the
  artifact first (edit spec/plan/tasks or re-run the Spec Kit command), or NEEDS DECISION
- it requires authorization that has not already been granted → BLOCKED
- every path forward is a guess → BLOCKED

## Finishing

Follow execution and completion ownership in `.aiek/core/WORKFLOW.md`: direct execution
invokes `verifying-change`, then `reviewing-change`, then reports DONE using
`.aiek/core/handoffs.md`. Under an upstream implementation command, return to its completion
hooks without repeating those gates or emitting DONE early. Integration uses `finishing-branch`.

## Red flags

- "I'll just also refactor…" → out of scope; note it as a follow-up
- "The plan is wrong, I'll do it my way" without updating the artifact → competing source of truth
- Ticking a task whose check you didn't run
- Asking the human "shall I continue to the next task?" → don't; continue

_Execution discipline adapted from `executing-plans` / `subagent-driven-development` of
obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
