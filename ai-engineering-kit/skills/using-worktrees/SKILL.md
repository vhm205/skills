---
name: using-worktrees
description: "Use when work needs its own isolated checkout - the canonical workflow requires isolation for Large work, the user says 'use a worktree' or 'work in a separate checkout', or concurrent work would collide in the main tree. Reuses existing isolation, prefers the harness's native workspace, falls back to a git worktree using the adapter's worktree_dir and branch_pattern, and finishes with setup plus a baseline run (verify.test_fast). Not for merging or cleaning up a branch (use finishing-branch), deciding which tasks can run concurrently (use parallel-development), or ordinary work that can safely use the current checkout."
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

If the kit installed `.aiek/scripts/worktree.py`, it selects the directory, name and branch from
the adapter and creates the checkout, then optionally runs setup and baseline:

```bash
python .aiek/scripts/worktree.py --adapter .aiek/adapter.md --slug <slug> --ticket <ticket-id> --setup --baseline --dry-run
```

Drop `--dry-run` to execute; it prints every git and setup command before running it, refuses an
existing path and never removes another worktree. Without the script, or when the adapter
overrides the layout, do it by hand:

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
2. Run the adapter's baseline checks (`verify.test_fast`, at minimum). This is the fast
   baseline; the full gate (`verify.test_full`) still belongs to verification before DONE.
3. Report one line: `Worktree ready at <path> on <branch>; baseline: <N passed, M failed>`.
   If the baseline has failures, list them. They are pre-existing, not yours. Continue
   unless they block the task, in which case report BLOCKED.

## Gotchas

- Creating a git worktree underneath a harness-provided workspace, which gives nested isolation.
- Reusing a branch already checked out elsewhere, silently borrowing another session's state.
- Assuming untracked spec/plan artifacts follow the branch; they must be copied deliberately.
- A new in-repo worktree directory missing from local excludes, polluting git status everywhere.
- Reading baseline failures as own regressions, or ignoring them without recording them.

## Cleanup

Leave the worktree in place until the work is merged or abandoned. `finishing-branch`
handles removal. Never `git worktree remove --force` without the human asking.

_Adapted from `using-git-worktrees` of obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
