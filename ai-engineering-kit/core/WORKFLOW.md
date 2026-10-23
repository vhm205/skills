# Canonical Workflow

This is the one workflow the kit follows. Skills, Spec Kit commands and adapters plug into it;
none of them define a competing flow.

```text
New project + BRD ──► bootstrap ──► shaping-project ──► Project Brief
                       ──► Spec Kit constitution ──► ROADMAP.md ──► human approval
                       ──► first MVP slice ──► classify lane below

Change request / approved roadmap slice
      │
      ▼
 Arrived as a ticket with acceptance criteria? ─yes─► intaking-ticket ─► criteria + traceability ─┐
      │ no                                             └─ not checkable ─► BLOCKED (questions)    │
      ▼                                                                                           │
 Unclear WHETHER to build it? ─yes──► exploring-idea ──► Idea Note ──► DROP / ASSESS / ...────────┤
      │ no                                                                                        │
 Unclear HOW it should work? ──yes──► shaping-feature ──► Feature Brief ──────────────────────────┤
      │ no                                                                                        │
      ▼◄────────────────────────────────────────────────────────────────────────────────────────┘
 Classify lane (core/classification.md)
      │
      ├─ INFRA ─────► shipping-infrastructure (always Large) ─► verifying-change
      │                 ─► reviewing-change ─► accepting-change (ops) ─► DONE
      │
      ├─ SMALL ─────► executing-task ─► verifying-change ─► reviewing-change ─► DONE
      │
      ├─ NORMAL ────► speckit specify ─► [clarify] ─► plan ─► tasks ─► READY TO BUILD
      │                 ─► executing-task (per task, parallel-development if [P])
      │                 ─► verifying-change ─► reviewing-change ─► DONE
      │
      └─ LARGE ─────► research / clarify ─► speckit specify ─► clarify ─► plan
                        ─► NEEDS DECISION (if a real trade-off remains)
                        ─► tasks ─► analyze ─► READY TO BUILD
                        ─► using-worktrees ─► executing-task / parallel-development
                        ─► verifying-change ─► reviewing-change (independent reviewer) ─► DONE

Before handing a change to reviewers, `authoring-pr` writes the description from the
verification evidence. Before release, `accepting-change` runs the acceptance pass.
```

If both value and behavior are unclear, explore whether to build it first (`exploring-idea`,
which may hand on to the Spec Kit `assess` extension). Once a spec exists, resolve requirement
ambiguity through `clarify`; do not restart discovery for the same feature. When the work
arrives from a tracker with acceptance criteria, `intaking-ticket` runs first and blocks on
criteria nobody can check.

## New projects

For an empty project, use the kit's `scripts/init-project.sh` with a BRD path and agent
integration. It initializes Spec Kit, installs the kit, and keeps the BRD under
`docs/inputs/`. `shaping-project` then creates only a Project Brief. The upstream
constitution command records engineering principles; `speckit.aiek.project-roadmap`
owns `ROADMAP.md`. Its MVP boundary and phase order require explicit human approval
before a slice is specified or built. An agent may orchestrate these stages, but a
textual approval claim is not a machine gate; use the `aiek-project` workflow gate
when running the supervised Spec Kit runner.

The roadmap owns project sequencing: phases are product milestones, MVP slices are
independent Spec Kit features. Only MVP slices are detailed initially. Select the first
ready slice and classify **that slice**, using intended behavior and risk rather than
the current file count. The selected lane follows the existing workflow. Stop after
one slice reaches DONE; revisit later phases and slice boundaries as evidence changes.
Each spec links to its roadmap ID, and the roadmap links back to the spec. If the
roadmap and a spec conflict, reconcile the roadmap boundary and then amend the spec.

## Stages and owners

| Stage | Owner | Output | Source of truth? |
|---|---|---|---|
| Discovery (should we build it?) | `exploring-idea` skill | Idea Note + a named exit | No, it is input to shaping or assessment |
| Discovery (how should it work?) | `shaping-feature` skill | Feature Brief | No, it is input to `specify` |
| Ticket intake (can each criterion be checked?) | `intaking-ticket` skill | Checkable criteria + traceability table | No, it is input to `specify` or to the Small lane |
| New-project discovery | `shaping-project` skill | Project Brief | No, it is input to roadmap |
| Project decomposition | Spec Kit `aiek` extension | `ROADMAP.md` | **Yes, for phase/slice scope and order** |
| Idea assessment (is it worth it?) | Spec Kit `assess` extension (optional) | Assessment verdict | No, it is input to `specify` |
| Requirements, WHAT/WHY | Spec Kit `specify` / `clarify` | `specs/<feature>/spec.md` | **Yes** |
| Technical plan, HOW | Spec Kit `plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/` | **Yes** |
| Task breakdown | Spec Kit `tasks` (+ `analyze` for Large) | `tasks.md` | **Yes** |
| Execution | `executing-task` (+ `using-worktrees`, `parallel-development`, `systematic-debugging`, `test-driven-development`) | Code, commits, execution log | Code only |
| Execution (infrastructure) | `shipping-infrastructure` | Recorded decision + ops evidence | Code and configuration only |
| Verification | `verifying-change` | Evidence (command, exit code, output) | — |
| Review | `reviewing-change` | Findings by severity | — |
| Pull request | `authoring-pr` (when the project uses PRs) | Description + author self-review | — |
| Acceptance | `accepting-change` | Acceptance sheet + sign-off, or ops evidence | — |
| Integration | `finishing-branch` (optional) | Merge / PR / keep | — |

Once `specify` has run, the Spec Kit artifacts are the **only** plan. Execution skills read them
and never write a second plan. If the plan turns out to be wrong, fix it in the artifact
(re-run or edit `spec.md`/`plan.md`/`tasks.md`), not in chat or in a side document.

The planner itself is selected by the adapter's `planning.mode`: `speckit` (default) means
`specs/<feature>/` owns the plan; `external` means the adapter's `planning.plan_path` and
`planning.task_source` do; `none` means no planning artifacts and only Small/infra work.
Whichever mode applies, exactly one artifact set owns the plan and every other document links
to it. Fact ownership (docs vs planner vs tracker vs evidence) is in
[documentation.md](documentation.md).

## Lanes in one line each

- **Small**: obvious change, 1–2 files, no new behavior worth specifying. Go straight to execution.
- **Normal**: a real feature or behavior change. Spec, plan, tasks, then execute.
- **Large / Risky**: several layers, irreversible operations, or a meaningful trade-off. Research
  first, plan carefully, put the decision to a human before tasks, use an isolated worktree,
  and get an independent review.

Lane rules are in [classification.md](classification.md). When unsure between two lanes,
pick the heavier one. You can step down later; stepping up after code exists is expensive.

## Bugs

Bugs use the same lanes. The difference is the first step:

- Investigate an unproven cause with `systematic-debugging`, then classify the fix.
  Small fixes go straight to execution; Normal/Large fixes use their Spec Kit path.
  Verification includes the original symptom as evidence.
- A bug whose fix changes intended behavior, or needs a design change, becomes a Normal/Large
  change and goes through Spec Kit. If the project installed the Spec Kit `bug` extension, its
  artifacts may replace `specify` for the bug report.

## Human checkpoints

Agents continue between authorized steps. Discovery questions and concise progress updates
are allowed; only handoffs use these three reports (see [handoffs.md](handoffs.md)):

- **BLOCKED**: it cannot safely continue.
- **NEEDS DECISION**: a product, architecture or trade-off choice that is not the agent's to make.
- **DONE**: verified and ready for review.

Several agents may run at once. Humans review their work one report at a time.

## Mandatory vs. optional

| Practice | Status |
|---|---|
| Verification before claiming DONE | **Mandatory, every lane** |
| Review before DONE | Mandatory; reviewer policy below |
| Spec Kit artifacts | Mandatory for Normal and Large; `planning.mode` selects Spec Kit or the external planner |
| TDD | Optional. Adapters or presets may require it per project |
| Isolation | Required for Large; native isolated workspace or worktree. Parallel work may use disjoint files per [parallelism.md](parallelism.md). Otherwise optional |
| Parallel execution | Only when [parallelism.md](parallelism.md) says the tasks are independent |

If the environment cannot provide isolation, use a separate branch with sequential execution
and disclose that limitation. Do not disturb unrelated working-tree changes; if a safe fallback
is impossible, report BLOCKED.

## Execution and completion ownership

- With Spec Kit `implement`, the upstream command owns task ordering and progress updates.
  `executing-task` supplies execution discipline within that loop, not a second loop.
  The `after_implement` hooks own verification, review and one DONE report. If hooks are
  missing, disabled or fail, run the same gates explicitly before claiming DONE.
- With direct skill execution (including Small), `executing-task` invokes verification and
  review and reports DONE itself. Parallel workers return evidence to their coordinator;
  only the coordinator reports combined completion.
- Reuse checks from the same unchanged state and scope. Targeted checks prove a task;
  the final gate covers the combined change. Re-run affected checks after review fixes.
- **Pull request ownership.** When a PR is the integration path, `authoring-pr` writes the
  description from verification evidence. `finishing-branch` chooses the disposition and reuses
  that description; it does not re-author the body, and no skill opens, pushes or merges a PR
  unless the person asked or the adapter's `integration` policy authorizes it.

## Reviewer policy

| Lane | Reviewer |
|---|---|
| Small | Self-review, labeled in DONE |
| Normal | Fresh reviewer when available and permitted; otherwise disclosed self-review |
| Large | Independent reviewer: fresh agent without author session history, or a human |

The adapter's `review.human_required_for` always requires a **human**, even if an independent
agent has reviewed it. If required review is unavailable, report BLOCKED with evidence ready
for review; do not label the work DONE. Review includes relevant uncommitted and new files.

## Project specifics

This file never names a language, test command, tracker or deploy target. Those come from the
active adapter: `.aiek/adapter.md` in an installed project (copied from `adapters/<name>/`). See [adapter-contract.md](adapter-contract.md)
for the machine-readable keys and [documentation.md](documentation.md) for who owns which fact.
