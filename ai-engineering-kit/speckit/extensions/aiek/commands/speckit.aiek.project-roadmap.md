---
description: "Create the project roadmap and MVP slices from a Project Brief"
---

## Input

```text
$ARGUMENTS
```

## Goal

Create the project-level `ROADMAP.md`. This Spec Kit extension owns product decomposition;
`.aiek/core/WORKFLOW.md` owns the stage order. Do not create `spec.md`, `plan.md`,
`tasks.md`, code, or a second roadmap.

## Steps

1. Read `docs/briefs/project-brief.md`, its source BRD, and
   `.specify/memory/constitution.md`. If the Brief is pending or a decision changes the MVP
   boundary, report NEEDS DECISION before writing the roadmap.
2. Define the project outcome and MVP hypothesis. List all project phases as product
   milestones with an observable exit outcome. Detail only the MVP phases. Later phases
   retain goals and candidate capabilities until their scope is revisited.
3. Split MVP into small, demonstrable slices. Each slice must be independently specifiable
   and verifiable. Give each a stable ID, intent, explicit in/deferred boundary,
   observable acceptance signal, BRD references, and dependency IDs. If one is still too
   large for a single Spec Kit feature, split it again. An MVP slice cannot depend on a
   later-phase capability. Avoid technical task lists.
4. Write `ROADMAP.md` with sections `Project outcome`, `MVP boundary`, `Phases`,
   `MVP slices`, `Open decisions`, and `BRD coverage`. The slice table columns are
   `ID | Phase | Slice | Intent | Boundary | Acceptance signal | BRD refs | Depends on |
   Status | Spec`. Use `planned` status and `—` for absent dependencies/spec links.
   Include `**MVP revision:** 1` and `**MVP decision:** pending` near the top. Increment
   the revision and reset the decision to pending whenever the MVP boundary or phase order
   changes. Preserve IDs after any spec links to
   them. Map every material BRD requirement to an MVP slice, later phase, explicit exclusion,
   or open decision. Do not silently drop one.
5. Present the MVP boundary, phase order, dependencies, exclusions, and open decisions to
   the owner for approval. Stop. Approval must be explicit before the first slice starts.

The roadmap owns project sequencing. Each later slice's `spec.md` owns its detailed
requirements; its `plan.md` and `tasks.md` own implementation planning. See the upstream
Spec Kit spec-of-specs convention for bidirectional roadmap/spec links.
