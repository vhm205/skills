---
name: shaping-project
description: "Use when a new project arrives as a BRD or requirements document with no established codebase - 'create a new project from this BRD', 'shape the project', 'write the project brief' - before any roadmap or feature specification exists. Reads the BRD, identifies users, outcomes, success signals, constraints and exclusions, and writes one Project Brief that maps every material requirement to an outcome, exclusion or open question. Not for feature shaping in an existing codebase (use shaping-feature), assessing whether an idea is worth doing (use exploring-idea), or writing the roadmap, constitution, specs or plans (Spec Kit owns those)."
---

# Shape a New Project

Read the source BRD and turn it into a short Project Brief. This is discovery for a whole
project, not a feature specification. The roadmap belongs to Spec Kit.

## Process

1. Read the BRD in `docs/inputs/` and any supporting requirements. Preserve section IDs or
   headings as source references. Never silently turn a proposed solution into an agreed need.
2. Identify primary users, their problems, desired outcomes, success signals, constraints,
   and explicit exclusions. Distinguish evidence from assumptions.
3. Ask the project owner only about missing choices that change the MVP boundary or the
   project's value. If viability itself is unclear, use the installed Spec Kit `assess`
   extension first when available.
4. Write `docs/briefs/project-brief.md` using `references/project-brief-template.md`.
   Map every material BRD requirement to an outcome, exclusion, or open question. Record
   recommendations as recommendations until the owner accepts them. Set `Status: ready`
   only when no unresolved choice changes the MVP boundary; otherwise use `Status: pending`.
5. Stop. The next step is the upstream Spec Kit constitution command, followed by
   `speckit.aiek.project-roadmap`. The Brief is historical input once the roadmap is approved.

## Boundaries

- Do not write a roadmap, phase list, slice list, feature spec, plan, tasks, or product code.
- Do not choose a technical stack unless the owner supplied it as a constraint.
- Read `.aiek/core/WORKFLOW.md` for stage ownership and handoffs.
