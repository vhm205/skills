## Project Task Evidence *(CHANGE-ME project)*

<!-- Example section appended to every task list. Replace or delete. -->

- Every task names the command that proves it (fast check or targeted test); a task without a
  check is not ready.
- Mark a task `[P]` only when the five independence rules in `.aiek/core/parallelism.md` hold
  (no file overlap, no ordering, no shared mutable state, understandable and verifiable alone).
- Keep the traceability link: acceptance criterion -> test layer -> acceptance case. Use
  `.aiek/scripts/traceability.py --file specs/<feature>/spec.md` to check for gaps.
- Record rulings in `execution-log.md` (a log, never a plan).
