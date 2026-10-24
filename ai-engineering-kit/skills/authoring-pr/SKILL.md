---
name: authoring-pr
description: "Use when writing or updating a PR/MR description from verification evidence, or preparing a verified change for reviewers - 'write the PR description', 'prepare this branch for review'. Picks the adapter's template or the kit sections, fills every number and claim from this session's evidence, runs the author self-review, lists related changes and merge order, and makes the prose readable. Not for choosing merge/PR/keep, pushing, merging or opening the PR (use finishing-branch), producing evidence (use verifying-change), or reviewing the code as a reviewer (use reviewing-change)."
---

# Authoring a Pull Request

Turn verified work into a description a reviewer can trust, and catch your own problems first.

The description is a **report of what happened**, not a pitch. Every number in it was produced
by `verifying-change` in this session.

## Before you start

You need, from this session: the verification evidence, the review findings, and the
traceability table if the work came from a ticket. Missing any of them means the change is not
ready for a PR — finish that step first.

## Step 1: pick the template

1. If the adapter names `pr_template`, read that file and use **its** sections in **its** order.
2. Otherwise use `references/pr-sections.md`.
3. If the adapter lists `pr_required_sections`, every one of them must be present and filled.
   **A missing required section stops the PR.** Say which one and why it cannot be filled.

Write in the language the adapter sets with `output_language`; default to the language the
repository's recent descriptions use.

## Step 2: fill it from evidence, not from memory

| Rule | What it means |
|---|---|
| **Numbers are verbatim** | Copy pass / fail / skip counts and blockers exactly as the run printed them. No rounding, no omitting the failures, no "all green" when it was not. |
| **Every claimed behavior gets a pointer** | A link to the test at this commit, a trace id, a log excerpt, an image of the real thing. One pointer per behavior. |
| **Missing evidence is written down** | If a behavior has no evidence, write that it is missing. Never fabricate a screenshot, a log line or a run. |
| **Limits are stated** | What was not verified, in what environment, with mocks or real dependencies, and what that leaves open. |
| **Scope limits are stated** | What was deliberately left out, and on whose decision. |

If the verification run was not green, the description says so and says why the change is being
shown anyway. A red run described as green is the one failure this skill exists to prevent.

## Step 3: self-review before asking anyone

Work through `references/self-review-checklist.md`. At minimum:

- Re-read the description against the ticket's scope: does it claim anything the ticket did not
  ask for, and does it miss anything the ticket did ask for?
- Re-read the description against the diff: does every section match what the code actually
  does?
- Run the repository's whitespace/diff sanity check.
- Walk the diff once as a reviewer would, looking for leftovers: debug output, commented-out
  code, unrelated reformatting, files you did not mean to touch.

## Step 4: related changes and merge order

List the open pull requests that touch the same files. Do not assume this change is
independent — check. For each overlap, say whether it must merge before or after, and what has
to be re-run once the other lands.

## Step 5: make the prose readable

The sections a human reads for meaning — the goal, the overview, the release note — are written
for someone who was not in this session. No internal jargon, no implementation vocabulary in a
sentence meant for a user.

If the adapter names a prose-rewrite command, run the prose through it, then **compare the
result against the original line by line for numbers, identifiers and terminology**. A rewrite
that improves the reading and changes a number is worse than no rewrite.

## Rules

- Do not open, merge or close the pull request unless asked. This skill writes the description;
  `finishing-branch` handles disposition.
- Do not re-run verification to get a better number. If the state changed, re-verify properly
  and replace the whole evidence block.
- An unverifiable claim is deleted, not softened.

## Red flags

- "All tests pass" without a count and a command
- An evidence table whose rows link to nothing
- A description written before the verification run finished
- Scope sections copied from the ticket without checking the diff
