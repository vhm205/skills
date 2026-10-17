---
description: Create or update the feature specification from a natural language feature description or a Feature Brief.
strategy: wrap
---

## Feature Brief Intake (AI Engineering Kit)

The input may be a **Feature Brief** produced by the `shaping-feature` skill (pasted, or a path
such as `docs/briefs/<date>-<slug>.md`). Recognize it by its headings (`Problem`,
`Users and desired outcome`, `Recommended direction`, `Scope`, `Open questions`). If it is a
path, read the file.

When the input is a Feature Brief, use it as follows and do not re-run discovery:

| Brief section | Use in spec.md |
|---|---|
| Problem; Users and desired outcome | Overview / context and the actors of the user stories |
| Recommended direction | Basis for the user stories and functional requirements (WHAT, not HOW) |
| Success signal | Success Criteria (make them measurable) |
| Scope In / Out / Anti-goals | Scope, out-of-scope, and negative requirements |
| Constraints and feasibility notes | Assumptions / constraints; keep implementation detail out of the spec |
| Open questions | `[NEEDS CLARIFICATION: ...]` markers (respect the core limit on markers; turn the rest into documented assumptions) |
| Assumptions marked "(assumed)" | Assumptions section, still marked as assumed |
| Options considered | Do not copy. Mention the chosen direction only |

Add a line under the spec header: `**Input**: Feature Brief <path or "inline">`.
From this point on, `spec.md` is the source of truth; the brief is history.

{CORE_TEMPLATE}
