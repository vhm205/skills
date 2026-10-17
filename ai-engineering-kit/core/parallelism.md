# When Work May Run in Parallel

Default: **sequential**. Parallel work is an optimization that has to earn its place.

## Two tasks are independent only if ALL of these hold

1. **No file overlap.** They do not edit the same files (including lockfiles, generated files,
   migrations, shared config, route tables, barrel/index files).
2. **No ordering dependency.** Neither consumes an interface, type, table or output the other
   creates or changes.
3. **No shared mutable state** at test time: same database, ports, fixtures, caches or
   external sandbox accounts, unless each task gets its own.
4. **Each is understandable alone.** A worker can finish it from its own brief without
   knowing what the other worker is doing.
5. **Each is verifiable alone.** It has its own check that passes without the other task.

If you cannot confirm all five from the plan and the code, treat the tasks as dependent.

## Source of the decision

- **Normal/Large lanes:** Spec Kit's `tasks.md` marks parallelizable tasks with `[P]`
  (different files, no dependency on incomplete tasks). `[P]` is a *candidate* signal. Re-check
  the five rules against the current code before dispatching. Spec Kit decides what may be
  parallel; `parallel-development` decides whether to actually do it now.
- **Small lane:** no parallelism, except for independent investigations (e.g. three unrelated
  failing tests with different causes).

## Not a reason to parallelize

- "It would be faster" with tasks in the same module
- Exploratory debugging where the cause is unknown
- Tasks whose briefs say "coordinate with" or "after"

## Integration rules

- Each parallel worker uses its own worktree or touches a disjoint file set.
- After workers return: read each diff (not just its report), check for conflicts, then run the
  **full** verification once on the combined result.
- Humans review the combined result sequentially; parallel workers never merge each other.
