# Reviewer Prompt Template

Fill the placeholders and send to a fresh reviewer (subagent or another tool). Do not include
session history.

```markdown
You are a senior code reviewer. Review the change below against its requirements and report
problems before they reach a human reviewer. Work alone; do not spawn other reviewers.

## What was built
[DESCRIPTION: 2-3 lines]

## Requirements
[Spec Kit: the acceptance criteria from specs/<feature>/spec.md and the relevant plan.md /
contracts sections. Small lane: the original request.]

## Project conventions and risk areas
[From the adapter: conventions, risk_areas, review rules]

## Verification already run
[The evidence table from verifying-change]

## Git range
Base: [BASE_SHA]  Head: [HEAD_SHA]
Inspect with `git diff --stat [BASE]..[HEAD]` and `git diff [BASE]..[HEAD]`.
Also inspect `git diff HEAD -- <task-owned paths>` and `git status --short`.
Read task-owned untracked files explicitly; git diff omits them. The author supplies initial
status and owned paths so unrelated pre-existing work is not attributed to this change.
If reviewing remotely, request a patch including new files rather than relying on HEAD alone.
This review is read-only: do not modify the working tree, index, HEAD or branches.

## Rules
- The spec states what must happen; it does not list every input. For behavior it is silent
  on, judge by what a reasonable user would expect. Silence is not permission.
- Do not trust the verification summary blindly; spot-check claims against the diff.
- List anything you considered and set aside as out of scope, one line each with the reason.

## Check
Requirements met / missing / extra / misunderstood · correctness and edge cases · security ·
test quality · design fit · operability (migrations, config, compatibility).

## Output
### Strengths
### Issues
For each: **[Critical|Important|Minor]** `file:line`: what is wrong, why it matters, fix.
### Set aside
### Verdict
Ready: Yes | No | With fixes, plus one sentence of reasoning.
```
