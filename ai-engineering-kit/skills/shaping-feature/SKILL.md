---
name: shaping-feature
description: "Shapes a Feature Brief when desired users, outcomes or behavior remain unclear before specification. Excludes clear requests, value/prioritization assessment, planning and implementation."
---

# Shaping a Feature

Turn a vague request into a short **Feature Brief** that a spec author (Spec Kit `specify`)
can work from. You explore. You do not plan, and you do not build.

<HARD-GATE>
This skill ends when the Feature Brief is written. Then STOP.
Do not write an implementation plan, task list, spec.md, code, scaffolding, or install
anything. Reading code and docs to inform the brief is fine.
</HARD-GATE>

## Is this the right skill?

| Situation | Go to |
|---|---|
| A spec already exists for this feature | use the upstream clarification command; do not create a competing brief |
| Request is clear: problem, user and expected behavior are known | skip this; classify the lane (`.aiek/core/classification.md`) |
| "Should we build this at all?" (value, cost, priority) | Spec Kit idea assessment (`assess` extension) if installed; else answer with a short assessment, not a brief |
| How it should work is unclear | **this skill** |

If the user says "skip the questions" or "just guess", write the brief from what you have,
mark every guess as `(assumed)`, and stop.

## Process

1. **Recon first, quietly.** Read what already exists (related code, docs, prior specs in
   `specs/`, the adapter's domain notes) so you don't ask what the repo already answers.
2. **Understand the real problem.** Ask about a concrete moment: who hits this, when, and what
   they do today. One question per message, a single plain sentence, no list of sample
   answers. Offer a short menu only if the person is stuck.
3. **Challenge assumptions.** Separate the problem from the proposed solution. Ask "what happens
   if we don't build this?" and "what would make this a failure?" when it helps.
4. **Explore solutions privately, show only what helps decide.** Think of several approaches,
   drop the weak ones, and present 2–3 only when the choice matters. For each: how it works,
   trade-offs, UX impact, technical feasibility (based on what you read), rough size.
5. **Play it back.** Summarize your understanding in a few short paragraphs, mark your guesses,
   and ask what is wrong or missing. Repeat until the person agrees or says "good enough".
6. **Write the brief** using `references/feature-brief-template.md`. Keep it under one page.
7. **Hand off and stop.** End with exactly:

   > Feature Brief ready. Next: run Spec Kit `specify` with this brief as input
   > (use the command name rendered by the installed integration, with the brief or its path).

## Where the brief goes

- Default: in the conversation. That is enough for `specify`.
- If the person wants it kept, or the adapter sets `brief_dir`, save it as
  `<brief_dir>/YYYY-MM-DD-<slug>.md` (default `docs/briefs/`). It is a historical input; once
  `spec.md` exists, the spec wins on any conflict.

## Rules

- Your recommendations are labeled as yours. Never record a choice as "agreed" unless the
  person said so.
- Options steer. State defaults out loud instead of hiding them in option order.
- WHAT and WHY belong here. Technology choices only appear as feasibility notes or constraints
  the person stated, never as a design.
- If the request is really several features, say so, propose an order, and shape only the first.
- If it turns out to be small and obvious, say so and stop early: write a three-line brief or
  skip the brief and send it straight to the Small lane.

## Red flags: you are leaving your lane

- Writing "Step 1… Step 2…" implementation steps, file lists, or task IDs
- Opening an editor on product code
- Deciding the database schema or API shape in detail
- Running `specify` yourself without the person's go-ahead

_Adapted from the `brainstorming` skill of obra/superpowers (MIT, © 2025 Jesse Vincent); license in the kit's `NOTICE.md`._
