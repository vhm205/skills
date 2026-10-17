# Canonical Workflow

This is the one workflow the kit follows. Skills, Spec Kit commands and adapters plug into it;
none of them define a competing flow.

```text
Change request
      │
      ▼
 Unclear HOW it should work? ──yes──► shaping-feature ──► Feature Brief ──┐
      │ no                                                               │
 Unclear WHETHER to build it? ─yes──► Spec Kit assess (idea assessment) ─┤
      │ no                                                               │
      ▼◄─────────────────────────────────────────────────────────────────┘
 Classify lane (core/classification.md)
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
```

If both value and behavior are unclear, assess whether to build first. Once a spec exists,
resolve requirement ambiguity through `clarify`; do not restart discovery for the same feature.

## Stages and owners

| Stage | Owner | Output | Source of truth? |
|---|---|---|---|
| Discovery (how should it work?) | `shaping-feature` skill | Feature Brief | No, it is input to `specify` |
| Idea assessment (should we build it?) | Spec Kit `assess` extension (optional) | Assessment verdict | No, it is input to `specify` |
| Requirements, WHAT/WHY | Spec Kit `specify` / `clarify` | `specs/<feature>/spec.md` | **Yes** |
| Technical plan, HOW | Spec Kit `plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/` | **Yes** |
| Task breakdown | Spec Kit `tasks` (+ `analyze` for Large) | `tasks.md` | **Yes** |
| Execution | `executing-task` (+ `using-worktrees`, `parallel-development`, `systematic-debugging`, `test-driven-development`) | Code, commits, execution log | Code only |
| Verification | `verifying-change` | Evidence (command, exit code, output) | — |
| Review | `reviewing-change` | Findings by severity | — |
| Integration | `finishing-branch` (optional) | Merge / PR / keep | — |

Once `specify` has run, the Spec Kit artifacts are the **only** plan. Execution skills read them
and never write a second plan. If the plan turns out to be wrong, fix it in the artifact
(re-run or edit `spec.md`/`plan.md`/`tasks.md`), not in chat or in a side document.

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
| Spec Kit artifacts | Mandatory for Normal and Large |
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
active adapter: `.aiek/adapter.md` in an installed project (copied from `adapters/<name>/`). See [adapter-contract.md](adapter-contract.md).
