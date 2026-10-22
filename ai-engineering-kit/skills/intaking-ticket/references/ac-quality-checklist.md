# Acceptance Criterion Quality Checklist

Run every criterion through this before accepting it into the traceability table.

## A criterion is usable when it has

1. **A starting state.** What is true before. Without it, the criterion cannot be set up.
2. **A trigger.** What someone or something does.
3. **An expected result, stated as an observation.** "X appears", "the call returns Y",
   "nothing is written to Z". Not "it works", not "correctly", not "as expected".
4. **One reason to fail.** If two things could break it independently, split it.

Given / When / Then is a convenient shape for 1-3, but the shape is not the point; the three
parts are.

## Four gaps to look for

| Gap | Symptom | Question to raise |
|---|---|---|
| **No expected result** | "The system handles invalid input" | "What should the user see, and what must not be saved?" |
| **Two behaviors in one** | "…rejects it and notifies the team" | "Should these be two criteria? Can one pass while the other fails?" |
| **No boundary named** | A range is mentioned but only the middle is tested | "What happens exactly at the first and last value, and just outside?" |
| **No error path** | Only the happy path is described | "What should happen when the dependency is slow, down, or returns an error?" |

## Qualities that need a threshold

A criterion using any of these words is not checkable until it carries a number and a unit:

fast · slow · responsive · reliable · stable · scalable · soon · frequently · rarely · most ·
usually · clear · simple · acceptable · reasonable

Convert it to: **metric · threshold · unit · measured under what conditions**.

Example: "replies are fast" → "p95 response latency under 3 s, measured at 50 concurrent
conversations". If you propose the numbers yourself, label them as assumptions and put them in
the question list anyway.

## Scope checks

- Does the criterion contradict anything the ticket lists as out of scope? That is a question.
- Does it depend on a system the ticket never mentions? Name the dependency.
- Does it require data or access that does not exist yet? That is a blocker, not a criterion.

## What not to do

- Do not rewrite a criterion into something easier to test and carry on silently. Propose the
  rewrite and let the requester accept it.
- Do not drop a criterion because it is awkward. Awkward belongs in the person-checkable
  bucket.
- Do not add criteria of your own invention to the table. Raise them as questions.
