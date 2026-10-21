---
description: "Classify and complete the first approved MVP slice"
---

## Input

```text
$ARGUMENTS
```

## Goal

Complete one MVP slice after explicit approval of `ROADMAP.md`. This command coordinates
the canonical lane path; it does not replace any Spec Kit core command or kit skill.

## Steps

1. Read `ROADMAP.md`, `.aiek/core/WORKFLOW.md`, `.aiek/core/classification.md`, and
   `.aiek/adapter.md`. Require explicit owner approval of the current MVP boundary and phase
   order, either recorded for the current MVP revision in the roadmap or supplied in the
   current conversation/workflow gate. A pending or changed roadmap needs fresh approval.
   Record `**MVP decision:** approved for revision <n> by <owner> on <date>` in
   `ROADMAP.md` before starting a spec. Otherwise stop with
   NEEDS DECISION.
2. Choose the first `planned` MVP slice whose dependencies are `done`. Use its stable ID;
   do not classify the whole project. If no such slice exists, report BLOCKED with the
   dependency or state mismatch. If a slice is too broad, revise the roadmap and seek
   approval again.
3. Classify this slice using `.aiek/core/classification.md` and its expected contracts,
   services, risk areas, and unknowns. An empty codebase does not imply SMALL. State the
   lane and reason. For NORMAL or LARGE, run the existing Spec Kit specify/clarify/plan/tasks
   path; LARGE also runs analyze and uses isolation and independent review. SMALL follows
   direct execution. Use the installed integration's rendered command names.
4. Put `**Input**: Parent roadmap: ROADMAP.md → <slice ID>` in the slice's `spec.md` when
   one is created, then fill the roadmap's `Spec` link. Execute, verify, and review using
   the existing lane. Mark the slice `done` only after its DONE evidence. Otherwise keep
   its actual status and handoff. Stop after this one slice.

When continuing later slices, repeat steps 2–4. Reconcile the roadmap first when BRD or
MVP scope changes; never treat a completed sibling spec as permission to change its scope.
