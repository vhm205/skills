---
name: using-worktrees
description: "Prepares isolation when the canonical workflow requires it or the user requests a separate checkout. Reuses existing isolation; not required for every task."
---

# Using Worktrees

Give the work its own isolated checkout so it cannot disturb the main working tree or other
agents.

## Step 0: already isolated?

```bash
[ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ] && echo "already in a worktree"
git rev-parse --show-superproject-working-tree   # non-empty → inside a submodule, don't nest
```

If already in a worktree, use it. Skip to Step 3.

## Step 1: prefer the harness's native isolation

If the agent harness provides an isolated checkout or per-task workspace, use it. Creating
a second worktree with git underneath it confuses the harness.

## Step 2: git fallback

1. **Directory**, first match wins:
   1. the adapter's `worktree_dir`
   2. an existing `.worktrees/` (preferred) or `worktrees/`
   3. create `.worktrees/`
2. **Ignore the selected directory** if it is inside the repository. Check that actual path
   with `git check-ignore`; use a local exclude or an authorized `.gitignore` edit. No separate
   commit is required. External worktree directories do not need a repository ignore rule.
3. **Branch name**: the adapter's `branch_pattern`, else the active feature branch/name,
   else `<type>/<slug>`. Inspect existing branches and `git worktree list` first.
4. Create the checkout under the selected directory. Use `-b` only for a new branch. If the
   feature branch already exists, reuse it only if not checked out elsewhere; otherwise use
   an available isolated checkout or a distinct execution branch. Never move another session.
5. Confirm spec/plan/tasks are available there. Uncommitted artifacts do not follow a branch;
   copy only the active feature's required artifacts, preserving their source and local edits.

If isolation is unavailable, use the fallback policy in `.aiek/core/WORKFLOW.md`.

**Never** start feature work directly on the default branch without explicit consent.

## Step 3: set up and baseline

1. Resolve `verify.setup` with `.aiek/core/command-discovery.md` when missing or `auto`.
   Run it if available; `null` means unavailable. Never overwrite an existing environment file.
2. Run the adapter's baseline checks (`verify.test`, at minimum).
3. Report one line: `Worktree ready at <path> on <branch>; baseline: <N passed, M failed>`.
   If the baseline has failures, list them. They are pre-existing, not yours. Continue
   unless they block the task, in which case report BLOCKED.

## Cleanup

Leave the worktree in place until the work is merged or abandoned. `finishing-branch`
handles removal. Never `git worktree remove --force` without the human asking.

_Adapted from `using-git-worktrees` of obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
