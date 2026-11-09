# Small changes: inline execution

This is the canonical Small execution path, regardless of installed profile. Use it only
when [classification.md](classification.md) confirms Small: clear scope, known cause,
trivial rollback and no hard risk trigger. Uncertainty is a reason to investigate or step up,
not a reason to call the task Small. Project instructions and adapter requirements still apply.

## One pass

1. Read the adapter and relevant code. Announce lane, scope and targeted checks in one short
   update, including estimates and any expensive gate, per [WORKFLOW.md](WORKFLOW.md).
2. Make the smallest authorized edit. For a known-cause bug, capture the original symptom
   with a failing test or scripted reproduction before fixing it. Apply project-required TDD.
3. Run the relevant checks after the final edit, read their output and compare against the
   project baseline. Confirm the original symptom and affected behavior. Report skipped or
   unavailable checks; never weaken checks or expand a baseline to make them pass.
4. Inspect the complete task diff, including new files, against the request. Check edge cases,
   security, scope and test coverage. Fix findings and rerun affected checks.
5. Report a compact DONE: change, actual commands/results, self-review and remaining risk.
   Use [handoffs.md](handoffs.md) for blockers or decisions. PRs still use `authoring-pr` when
   requested; release acceptance and project-required human review remain separate gates.

These steps satisfy execution, verification and self-review inline. Do not load
`executing-task`, `verifying-change` and `reviewing-change` solely to repeat these steps,
create separate stage reports, or rerun checks on unchanged state and scope. Load a skill
only for guidance needed by the actual problem. Do not create spec/plan/tasks for Small work.

## Escalation

- Unknown cause: use `systematic-debugging` before classifying the fix. Local source and a
  reproduction can establish the cause; ask only for missing context needed to investigate.
- Scope grows, acceptance criteria become ambiguous, or a classification hard trigger
  appears: stop the inline path and follow the required discovery or heavier lane.
- A required skill, planner or project review is unavailable: report the exact missing
  prerequisite. A reduced installation never permits skipping that stage.

## Installation profile

`--profile lite` installs only `executing-task`, `systematic-debugging`, `verifying-change`,
`reviewing-change` and `authoring-pr`, plus the same canonical core, adapter and helpers.
It suits Small work and standalone diff review. It does not provide discovery, planning,
release acceptance, worktrees or parallel-work skills. Install the needed skills or upgrade
with `--profile full` before following those paths; do not improvise replacements.

Profiles select installed skills, not risk policy. Existing installs are additive: installing
lite over full does not remove old skills. Use a fresh project for a clean lite measurement;
remove old kit-owned skills explicitly if deliberately reducing an existing installation.
