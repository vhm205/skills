---
name: finishing-branch
description: "Integrates completed, verified and reviewed work when a merge, pull request or branch disposition is requested or configured."
---

# Finishing a Branch (optional)

## 1. Verify first

Use `verifying-change` evidence for the final state; reuse it if scope and state are unchanged.
If anything fails, stop. The options below come only after a green run.

## 2. Confirm the base

Detect the base branch (`git merge-base`, the adapter's `default_branch`) and confirm in one
line: "This branch split from `<base>`."

## 3. Offer exactly these options

1. Merge into `<base>` locally
2. Push and open a pull request
3. Keep the branch as-is

Wait for the person's choice. Pushing, merging and deleting are hard to undo; never pick for
them unless the adapter's `integration` policy or the person's standing instruction says so.
Discarding work is offered only if the person asks, and needs them to type `discard`.

## 4. Execute

- **Merge:** merge, re-run the checks on the merged result, then remove the worktree and
  delete the branch (`git branch -d`, never `-D` without asking).
- **PR:** push the branch, open the PR using the adapter's PR template if any, and put the DONE
  report (summary, checks, evidence, risks) in the description. Keep the worktree.
- **Keep:** report the branch and worktree path.

## 5. Clean up

Remove only worktrees this workflow created (under the adapter's `worktree_dir` or
`.worktrees/`). Never `--force`. If removal is refused, show what is uncommitted and ask.
Never force-push unless explicitly asked.

_Adapted from `finishing-a-development-branch` of obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
