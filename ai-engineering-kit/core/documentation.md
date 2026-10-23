# Documentation Authority

Where each kind of fact lives, so planning artifacts never turn into a second set of docs.
Apply this whenever a skill is about to write a plan, a spec, a status update or project
documentation.

## Fact owners

| Fact | Owner | Must not also live in |
|---|---|---|
| Product intent, users, outcomes, roadmap, decision log | The project's durable product docs (adapter may name them) | A feature spec, a second roadmap, chat |
| Architecture, API contracts, runbooks, guides | The project's durable engineering docs | A feature plan, task list |
| Scope, behavior and acceptance criteria for **one slice** | The active planner artifact: `specs/<feature>/spec.md` for `speckit`, or the external planner's spec for `external` | Product docs (link instead), chat |
| Technical plan, data model, contracts, task breakdown for one slice | The same active planner (`plan.md`, `tasks.md`, `data-model.md`, `contracts/`) | A separate plan file, a task list in the tracker |
| Engineering principles the plan is checked against | The project's constitution or durable principles doc | The adapter |
| Commands, conventions, risk areas, review rules | `.aiek/adapter.md` | Any skill, any plan |
| Status and progress (who is doing what, what is done) | The tracker/issue system the project uses | Markdown "status" sections, `ROADMAP.md`, execution logs |
| Verification evidence and acceptance records | The project's QA/evidence location | A summary that cannot be re-checked |
| Agent operating instructions | `AGENTS.md`/`CLAUDE.md`, `.aiek/`, `.specify/memory/constitution.md` | Skill bodies, specs |

If a project has no explicit owner for a fact, propose one in the change and link to it; do not
invent a parallel document.

## Rules

1. **One fact, one owner.** Every fact has exactly one authoritative home. Elsewhere it is a
   link, a quote with a pointer, or absent.
2. **A feature spec is a slice, not a PRD.** It links to the product docs, architecture and QA
   cases it depends on. It repeats only the delta: what this slice must do, for whom, why, and
   how it will be proven.
3. **The roadmap is a thin index.** It lists phases and slices with links and status pointers;
   it does not restate specs or hold execution detail.
4. **Never create a second plan.** Read `planning.mode` from the adapter:
   - `speckit` — `specs/<feature>/` owns the plan and tasks.
   - `external` — the adapter's `planning.plan_path` and `planning.task_source` own them.
   - `none` — no planning artifacts; only Small/infra work is in scope.
   Execution skills read that source and fix it in place when it is wrong.
5. **Status lives in the tracker.** A plan artifact records scope and decisions, not a live
   status board. Do not add "Status: in progress" to durable docs.
6. **Legacy planners are archived, not migrated.** Mark old plan folders/specs as read-only or
   archived and point new work at the active planner. Do not bulk-copy history into the new
   structure, and do not run two planners in parallel.
7. **Conflicts are resolved at the owning layer.** If docs and a spec disagree, the durable
   product/architecture layer wins and the spec is amended; if the disagreement is about this
   slice's intended behavior, the spec wins and the product docs are clarified. Reconcile one
   layer, then the other — never both by copying text around.
8. **Evidence is a command and its output.** Link or quote the verification record; do not
   restate a pass count without its command.
9. **Language:** `output_language` from the adapter applies to PR bodies, reports, acceptance
   sheets and user-facing prose. Code, identifiers, paths and spec IDs stay as written.

## Where a skill writes what

| Skill | May write | Never writes |
|---|---|---|
| `shaping-feature`, `shaping-project`, `exploring-idea` | A brief or idea note, or the planner's input file when asked | A spec, plan or task list |
| `intaking-ticket` | A traceability table in the ticket or the planner's input | A second plan |
| `executing-task` | Code, commits, the execution log `specs/<feature>/execution-log.md` (a log, not a plan), ticked tasks | Requirements or plan changes without updating the artifact |
| `verifying-change`, `reviewing-change` | Evidence and findings in the report | A plan |
| `authoring-pr`, `finishing-branch` | PR description and disposition | A plan, a second PR description |
| `accepting-change`, `shipping-infrastructure` | Acceptance/ops evidence sheets | A roadmap, a spec |

## Using this file in a project

Installed at `.aiek/core/documentation.md`. The adapter can point at the project's actual doc
paths in its prose section (for example "product docs live in `docs/product/`, architecture in
`docs/architecture/`"). This file stays project-agnostic and wins only on **structure**; the
adapter wins on **paths**.
