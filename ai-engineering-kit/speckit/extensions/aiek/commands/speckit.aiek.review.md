---
description: "Review the implemented change against spec and plan, fix findings, and emit the DONE report"
---

## User Input

```text
$ARGUMENTS
```

## Goal

Get the implemented feature reviewed at the level its lane requires, resolve the findings,
and hand off with a single DONE report.

## Steps

1. Requires a passing `__SPECKIT_COMMAND_AIEK_VERIFY__` result from this session. If there is
   none, run that first.
2. Load `reviewing-change` and the reviewer policy in `.aiek/core/WORKFLOW.md`.
   Honor `review.human_required_for`: an agent cannot substitute for a required human.
   Include all task-owned changes, including staged, unstaged and untracked files.
3. Follow the skill's fix/review loop. Re-run affected verification after fixes. If required
   review is unavailable or blocking findings remain, report BLOCKED or NEEDS DECISION and
   stop before DONE.
4. If a finding means the spec or plan itself is wrong, do not patch around it: report NEEDS
   DECISION and name the artifact section to change.
5. Emit the **DONE** report exactly as in `.aiek/core/handoffs.md`, including the verification
   table, rulings from `specs/<feature>/execution-log.md` (if present), review findings fixed
   and deferred, and remaining risks.
6. Suggest the `finishing-branch` skill as the optional next step. Do not merge or push.
