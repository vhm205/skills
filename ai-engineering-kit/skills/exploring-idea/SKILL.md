---
name: exploring-idea
description: "Explores a raw idea, a complaint, or an architecture question when it is not yet clear whether anything should be built, or which direction to take. Produces an Idea Note and ends in one of: drop it, shape it, assess it, or a decision for a human. Excludes requests that are already decided (use feature shaping) and anything with an existing spec."
---

# Exploring an Idea

Take something that is not yet a change request — a complaint, a hunch, "should we…", or an
architecture fork — and turn it into an **Idea Note** that ends in a named next step.

This is the only skill allowed to conclude **"do not build this"**.

<HARD-GATE>
This skill ends when the Idea Note is written and you have named the next step. Then STOP.
No plan, no task list, no spec, no code, no scaffolding. Reading code and docs is fine.
</HARD-GATE>

## Is this the right skill?

| Situation | Go to |
|---|---|
| A spec already exists | the upstream clarification command; do not reopen discovery |
| It is decided we build it; only *how* is unclear | `shaping-feature` |
| A ticket exists with acceptance criteria | `intaking-ticket` |
| Whether to build it is unclear, or the problem itself is unclear | **this skill** |
| A technical fork with no obvious default (architecture, platform, pipeline) | **this skill**, ending in NEEDS DECISION |

## Process

1. **Find the problem under the request.** An idea usually arrives as a solution. Ask what
   goes wrong today, for whom, and how often. One question per message, plain sentences.
2. **Look for evidence before opinions.** Check what the repo, logs, tickets or existing
   artifacts already say. An idea with no evidence of the problem is a finding, not a failure —
   write it down as "no evidence found".
3. **Generate options, including doing nothing.** Three to five directions. **"Do nothing" is
   always one of them**, with what it costs. Drop the weak ones yourself; present only the
   ones that change the decision.
4. **Size each option roughly.** Order of magnitude only: hours / days / weeks, what it would
   touch, and what becomes hard to reverse. Do not design anything.
5. **Write the Idea Note** using `references/idea-note-template.md`. One page.
6. **Name the next step and stop.** Exactly one of the four below.

## The four exits

| Exit | When | What you output |
|---|---|---|
| **DROP** | The problem is not real, is already solved, or is not worth the cost | The note plus one sentence on what would change your mind |
| **SHAPE** | Worth building, but how it should work is unclear | The note, then hand to `shaping-feature` |
| **ASSESS** | Worth considering, but the value needs quantifying or prioritizing against other work | The note, then hand to the Spec Kit idea-assessment extension if installed; otherwise hand the note to a human |
| **NEEDS DECISION** | A real trade-off with no default, usually architectural or operational | A NEEDS DECISION report per `.aiek/core/handoffs.md`, with the trade-off table and the cost of being wrong |

End with one line naming the exit, for example:

> Idea Note ready. Exit: SHAPE. Next: `shaping-feature` for the "export reports" direction.

## Architecture and operations forks

When the idea is a technical fork rather than a product one, keep the same process but weight
the note toward:

- **Real constraints first.** What the current system actually requires (hardware, network
  mode, protocol, data locality). A constraint you discovered beats an option you imagined.
- **What becomes irreversible.** Name it explicitly; it decides how much the choice costs.
- **The cost of being wrong per option**, not just the benefit of being right.

Once a human decides, the decision belongs in the Spec Kit `plan.md` as a recorded decision
(see `shipping-infrastructure`). Do not keep it only in chat, and do not create a second
planning document for it.

## Rules

- Separate the problem from the proposed solution, out loud, in the note.
- Label your recommendation as yours. Never record a choice as agreed unless it was.
- Do not quantify value you cannot support. "Unknown" is a valid entry.
- If the idea is really several ideas, say so and explore only the one with the clearest
  problem.
- If the answer turns out to be obvious and small, say so and send it straight to the Small
  lane — a three-line note is a success, not a shortcut.

## Red flags: you are leaving your lane

- Writing implementation steps, file lists or task IDs
- Choosing a schema, an API shape, or a deployment topology in detail
- Running a spec or planning command yourself
- Presenting options with no "do nothing" row
- Recommending a direction you found no evidence for
