---
description: Generate an actionable, dependency-ordered, verifiable tasks.md for the feature.
strategy: wrap
---

## Before generating tasks (AI Engineering Kit)

Resolve the active feature using the upstream prerequisite procedure. Read `plan.md` before
creating or replacing tasks.md. If decisions remain unresolved, report NEEDS DECISION using
`.aiek/core/handoffs.md` and stop; do not run the generation procedure below. If a new trade-off
appears during generation, stop without replacing existing tasks with a guessed breakdown.

{CORE_TEMPLATE}

## Additional Task Rules (AI Engineering Kit)

Apply these while generating tasks.md (they tighten, never loosen, the rules above):

1. **`[P]` is strict.** Mark a task `[P]` only if, against every other `[P]` task in the same
   phase, it has no shared file (including lockfiles, migrations, route tables, index/barrel
   files, shared config), no dependency on their outputs, and no shared test state. See
   `.aiek/core/parallelism.md`. When in doubt, leave `[P]` off.
2. **Every phase checkpoint is verifiable.** End each phase's **Checkpoint** line with
   `Verify: <command or concrete manual check>`. Take commands from `.aiek/adapter.md`
   (`verify.*`) when available.
3. **Tests per adapter.** If `.aiek/adapter.md` sets `tdd: required` (or the feature touches
   `tdd_required_paths`), include test tasks before their implementation tasks even if the spec
   did not request tests.
