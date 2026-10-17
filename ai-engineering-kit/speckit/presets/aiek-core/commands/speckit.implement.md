---
description: Execute the implementation plan by processing all tasks in tasks.md with the AI Engineering Kit execution discipline.
strategy: wrap
---

## Execution Discipline (AI Engineering Kit)

These rules apply throughout the procedure below. Where they are stricter, they win.

- **Readiness first:** before changing code, invoke `__SPECKIT_COMMAND_AIEK_READY__` for
  the same active feature resolved by the upstream prerequisite check. Continue only on
  READY TO BUILD; BLOCKED or NEEDS DECISION ends this invocation.
- **One task loop:** upstream owns ordering and task progress. Apply `executing-task`
  discipline inside that loop, following `.aiek/core/WORKFLOW.md` for completion ownership.
- **Policy:** read `.aiek/core/WORKFLOW.md`, `.aiek/core/parallelism.md` and `.aiek/adapter.md`.
  Apply their isolation, parallelism, TDD and reviewer requirements. Large work must complete
  analysis before implementation. A workflow named Normal never overrides a Large classification.
- **Failures:** use `systematic-debugging` for unproven causes. Respect authorization and
  handoffs in `.aiek/core/handoffs.md`; do not ask again for already-authorized steps.
- **One completion:** the mandatory `after_implement` hooks run
  `__SPECKIT_COMMAND_AIEK_VERIFY__`, then `__SPECKIT_COMMAND_AIEK_REVIEW__`.
  If hooks are absent, disabled or unreadable, invoke these gates explicitly. Do not emit
  DONE if a gate fails or required review is missing. The upstream completion report uses
  the review hook's DONE result rather than generating a second handoff.

{CORE_TEMPLATE}
