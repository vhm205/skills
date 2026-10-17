# Worker Brief Template

```markdown
You are implementing one task in an isolated workspace. Work alone; do not spawn subagents.

## Task
<Task ID and text, verbatim from tasks.md, or the problem statement>

## Requirements (excerpts)
<Only the spec.md / plan.md / contracts sections this task depends on>

## Workspace
- Path: <worktree path> on branch <branch>, BASE <sha>
- You own: <files/dirs you may change>
- Do not touch: <files other workers own; shared lockfiles, migrations, config>

## Constraints
- Follow the conventions in <adapter path>.
- Smallest change that satisfies the task. No unrelated refactors.
- Do not "fix" failures by loosening tests, raising timeouts or skipping checks.

## Checks to run before reporting
<exact commands>

## Report (first line is the status)
DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- What changed (files)
- Check commands run and their results
- Rulings you made (what, why, cost if wrong)
- Concerns or open questions
```
