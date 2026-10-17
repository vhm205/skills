---
name: parallel-development
description: "Evaluates independent ready tasks or unrelated proven failures when concurrent workers are available and permitted. Falls back to sequential execution."
---

# Parallel Development

Run genuinely independent work concurrently, and keep everything else sequential.

## Step 1: decide

Take the candidate set (unfinished `[P]` tasks in the same phase, or unrelated failures).
Check every pair against the independence and integration rules in `.aiek/core/parallelism.md`.

Write the decision down in one line before dispatching, for example:
`Parallel: T012, T013, T014 (separate modules, separate test files). Sequential: T015 (needs T012's type).`

If any rule is uncertain for a pair, run that pair sequentially. If no subagent/parallel
facility exists in this harness, run the tasks sequentially. Correctness does not depend
on parallelism.

## Step 2: prepare isolation

Each worker gets its own worktree (`using-worktrees`) or a disjoint file set that you name
in its brief. Record the current commit as BASE.

## Step 3: dispatch

Send all independent workers in one go. Each brief uses `references/worker-brief.md`
and contains only what that worker needs: the task text, the spec/plan excerpts it depends
on, the files it owns, the files it must not touch, the checks to run, and the report format.
Never paste the whole session history.

Choose the model per task: mechanical tasks can use a cheaper model; anything requiring
judgment gets a capable one.

## Step 4: integrate

1. Read each worker's **diff**, not just its report.
2. Check for overlapping edits or contradictory assumptions.
3. Merge results into the integration branch one at a time.
4. Run the **full** verification once on the combined result (`verifying-change`).
5. Tick the completed tasks in tasks.md.

If a worker returns BLOCKED or NEEDS DECISION, keep the other workers' results, and surface
that report to the human in the sequential review queue.

## Red flags

- Two workers editing the same lockfile, migration folder, or route table
- A worker brief that says "coordinate with the other agent"
- Trusting "all tests pass" from a worker without re-running the suite after integration

_Adapted from `dispatching-parallel-agents` / `subagent-driven-development` of
obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
