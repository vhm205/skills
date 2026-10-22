---
name: intaking-ticket
description: "Turns a ticket or user story that already carries acceptance criteria into criteria a machine or a person can actually check, and into a traceability table linking each criterion to the test layer and acceptance case that will prove it. Use before classifying the lane when work arrives from a tracker. Excludes vague ideas with no criteria and requests already covered by a spec."
---

# Taking In a Ticket

A ticket arrives with a user story, acceptance criteria and business rules. Before any lane is
chosen, decide **how each criterion will be proven** — and send back the ones that cannot be.

<HARD-GATE>
If any acceptance criterion cannot be checked as written, stop and report **BLOCKED** per
`.aiek/core/handoffs.md` with the questions for whoever owns the requirements. Do not classify
the lane, do not write a spec, do not code, and do not invent the missing criterion.
</HARD-GATE>

## Is this the right skill?

| Situation | Go to |
|---|---|
| No criteria, and it is unclear whether to build it | `exploring-idea` |
| Decided to build, but how it should work is unclear | `shaping-feature` |
| A spec already exists | the upstream clarification command |
| A ticket with acceptance criteria, however rough | **this skill** |

## Process

1. **Read the whole ticket**, including scope, out-of-scope and business rules. Read the linked
   artifacts. Note which rules are referenced by which criteria.
2. **Classify every criterion** into one of three buckets (see below).
3. **Convert what can be converted.** A criterion stating a quality ("fast", "reliable",
   "clear") becomes a **threshold with a unit** before it counts as checkable. If you can pick
   the threshold from existing evidence in the repo, do so and label it as your assumption.
4. **Write the questions** for the unverifiable ones. One question per criterion, phrased so a
   non-engineer can answer it in a sentence. Do not bundle.
5. **Build the traceability table** (below). It is the artifact the rest of the workflow reads.
6. **Exit**: all criteria checkable → say so and classify the lane
   (`.aiek/core/classification.md`). Otherwise → BLOCKED with the questions.

## The three buckets

| Bucket | Means | Consequence |
|---|---|---|
| **Machine-checkable** | A test can fail when the behavior is wrong | Gets a test layer in the table |
| **Person-checkable** | Real, observable, but no test can run it (model output, visual judgement, a third party) | Gets an acceptance case in the table |
| **Not checkable as written** | Cannot be observed, or the expected result is not stated | Gets a question; blocks the ticket |

"Not checkable" is about the criterion, not about effort. A criterion that is merely expensive
to test is machine- or person-checkable and stays in the ticket.

## The traceability table

Produce one row per criterion. It travels with the work: `test-driven-development` picks the
layer, `authoring-pr` cites the evidence, `accepting-change` builds the acceptance sheet.

| Criterion | Rule(s) it enforces | Bucket | Proven by | Acceptance case |
|---|---|---|---|---|
| AC-01 … | BR-01 | machine | <lowest test layer that can prove it, per the adapter> | — |
| AC-02 … | BR-02 | person | — | UAT-01 |
| AC-03 … | — | not checkable | — | **question raised** |

Rules:

- **Every criterion gets a row.** A criterion with no row is a criterion nobody will check.
- **Pick the lowest layer that can prove the behavior**, from the adapter's test-layer table.
  Do not promise an end-to-end test for something a unit test can prove.
- **Edge cases count as criteria.** If the ticket lists boundary values or error paths
  separately, give each its own row.
- A criterion that only a person can check must still name what makes it pass, in observable
  words.

## Quality of criteria

Check each criterion against `references/ac-quality-checklist.md` before accepting it. The
common failures: no stated expected result, two behaviors in one criterion, a boundary value
nobody named, and no error path.

## Rules

- Do not invent an acceptance criterion the requester did not state. Propose one as a question.
- Do not widen scope. Anything listed as out of scope stays out; if a criterion contradicts it,
  that is a question, not a decision.
- Assumptions you make (thresholds, units, defaults) are listed explicitly and labeled.
- When the ticket is really several stories, say so and intake only the first, naming the rest.

## Red flags

- Writing implementation steps or a task list
- Filling a gap in the criteria with your own guess and continuing
- Promising "covered by end-to-end tests" for everything
- A table where several criteria share one row
