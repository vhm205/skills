# Lane Classification

Classify **after** any discovery (Feature Brief or assessment) and **before** writing code.
State the lane and the one-line reason at the start of the work, for example:
`Lane: NORMAL (new user-visible behavior across API + UI, reversible)`.

## Step 1: check for hard triggers (any one means LARGE)

Apply these to changes in behavior or operations. Merely mentioning a risk area in copy or
documentation does not trigger Large; changing its contract or operational procedure does.

- Data migration, schema change on shared or production data, or other irreversible operation
- Auth, permissions, tenant isolation, billing/payments, secrets handling
- Changes to a public API/contract that other teams or customers consume
- Infrastructure, deploy pipeline, or release process changes
- More than one service or deployable unit changes together
- A meaningful product or architecture trade-off with no clear default
- The adapter lists the touched area under `risk_areas`

## Step 2: otherwise, score the change

| Signal | Small | Normal | Large |
|---|---|---|---|
| Behavior | none or obvious (typo, copy, config value, rename, clear bug with a known cause) | new or changed behavior a user or caller notices | new capability or cross-cutting behavior |
| Files / layers | 1–2 files, 1 layer | several files, usually 1–2 layers | many files or 3+ layers |
| Unknowns | none | a few, answerable by reading code or one `clarify` round | needs research, spikes, or a decision |
| Rollback | trivial revert | revert plus maybe a data fix | hard or impossible |
| Acceptance criteria | obvious from the request | worth writing down | must be written down and agreed |

Take the **highest** column that any row lands in.

## Step 3: lane → required path

| Lane | Required | Optional |
|---|---|---|
| **SMALL** | `executing-task` → `verifying-change` → self-review via `reviewing-change` → DONE | TDD, worktree |
| **NORMAL** | Spec Kit `specify` → `clarify` (if the spec has `[NEEDS CLARIFICATION]`) → `plan` → `tasks` → `executing-task` → `verifying-change` → `reviewing-change` → DONE | `checklist`, `analyze`, worktree, parallel tasks |
| **LARGE** | research → `specify` → `clarify` → `plan` → **NEEDS DECISION if a trade-off remains** → `tasks` → `analyze` → `using-worktrees` → `executing-task` → `verifying-change` → `reviewing-change` by an **independent reviewer** (subagent or human) → DONE | TDD (often required by adapter), `checklist` |

## Changing lane mid-flight

- **Step up** as soon as you discover a hard trigger or the change outgrows its lane.
  Stop coding, say so in one line, and start the heavier path from the right stage.
  Work already done becomes input (link the diff in the spec), not a substitute for the spec.
- **Step down** only before code is written, and say why.

## Anti-ceremony rule

Do not run Spec Kit for SMALL work. A one-line copy fix with a spec, plan and tasks file is a
process failure, just as a migration without one is.
