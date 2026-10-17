---
description: Execute the implementation planning workflow, surfacing unresolved trade-offs as a decision gate.
strategy: wrap
---

{CORE_TEMPLATE}

## Decision Gate (AI Engineering Kit)

After the plan artifacts are written:

1. Read `.aiek/adapter.md` (if present). Any planned change touching its `risk_areas`, or any
   hard trigger in `.aiek/core/classification.md`, makes this a **LARGE** feature. Write
   `**Lane**: LARGE (<reason>)` or `**Lane**: NORMAL` near the top of `plan.md`.
2. Collect every choice in `research.md` / `plan.md` that (a) changes what gets built or how it
   can be undone, and (b) has no clear conventional default. Choices with a sensible default
   are not decisions: record them in research.md as "Decision / Rationale / Alternatives".
3. If any such choice remains, add a `## Decisions Needed` section to `plan.md` and end your
   response with a **NEEDS DECISION** report in the format of `.aiek/core/handoffs.md`
   (options, trade-offs, recommendation, decision required). Do not suggest running tasks yet.
4. When the human decides, record the outcome in `plan.md` (move it from "Decisions Needed" to
   the relevant section with the rationale), then continue to tasks.
5. If nothing remains, say `No open decisions` and hand off to tasks as usual.
