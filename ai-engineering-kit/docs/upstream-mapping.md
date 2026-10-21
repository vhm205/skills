# Upstream Mapping

What the kit takes from GitHub Spec Kit (1.2.2.dev0, c6a4c18) and obra/superpowers (v7.0.0,
bb92a77), and how. Categories:

- **Reuse**: used directly, unchanged, from the upstream install.
- **Wrap**: upstream stays authoritative; the kit adds rules around it at install time.
- **Adapt**: rewritten as a smaller kit skill with the same core discipline.
- **Exclude**: intentionally not used, with the reason.

## Spec Kit

| Upstream piece | Treatment | Notes |
|---|---|---|
| `constitution`, `clarify`, `analyze`, `checklist`, `converge` | Reuse | Called directly by the lanes |
| `specify` | Wrap (preset `aiek-core`) | Adds Feature Brief intake: brief sections map to spec sections |
| `plan` | Wrap | Adds lane marking and a `Decisions Needed` → NEEDS DECISION gate |
| `tasks` | Wrap | Stricter `[P]`, `Verify:` per checkpoint, TDD tasks when the adapter requires them, refuses with open decisions |
| `implement` | Wrap | Delegates the loop to the kit's execution skills; DONE only after verify/review hooks |
| Templates (`spec-`, `plan-`, `tasks-template.md`) | Reuse | Projects override them via their adapter's `speckit-preset/` |
| Hook system (`after_tasks`, `after_implement`) | Reuse | Extension `aiek` registers READY TO BUILD, verify, review as mandatory hooks |
| `assess` extension (idea assessment) | Reuse (optional) | The "should we build this?" path. Install with `specify extension add assess` |
| Project roadmap | Extend (`aiek` extension) | BRD/Project Brief → shallow `ROADMAP.md`; each approved MVP slice returns to the core SDD commands |
| `bug` extension | Reuse (optional) | May replace `specify` for bug reports; the kit does not require it |
| Workflow engine and `gate` steps | Reuse | Kit workflows `aiek-normal`, `aiek-large` |
| New-project workflow | Reuse | `aiek-project` supervises Project Brief → constitution → roadmap approval → first slice |
| Bundles | Exclude (v0) | A local bundle cannot carry its own extension/workflow payloads; components must come from a catalog. `install.sh --speckit` registers them with `--dev` instead |
| `taskstoissues` | Exclude | Deprecated upstream; tracker sync is an adapter concern |
| Agent integrations (skills rendering per agent) | Reuse | `specify init --integration <agent>` renders Spec Kit commands; the kit only installs its own skills |

## Superpowers

| Upstream skill | Treatment | Kit skill | What changed |
|---|---|---|---|
| brainstorming | Adapt | `shaping-feature` | Hard stop at a Feature Brief; hands off to `specify` rather than writing-plans; no design doc in `docs/superpowers/specs`; no visual companion server; narrow trigger (vague requests only) |
| writing-plans | Exclude | — | Spec Kit owns planning (`plan`, `tasks`) |
| executing-plans, subagent-driven-development | Adapt | `executing-task` | Reads Spec Kit `tasks.md` (T001/[P]/[USn]) rather than `## Task N`; rulings go to `execution-log.md`; anything contradicting the spec goes back to the artifact rather than the executor ruling over it; no ledger scripts |
| dispatching-parallel-agents (+ SDD's per-task model choice) | Adapt | `parallel-development` | Explicit 5-rule independence test; `[P]` from Spec Kit is a candidate, not a command |
| using-git-worktrees | Adapt | `using-worktrees` | Adapter-driven dir/branch/setup; branch defaults to the Spec Kit feature dir |
| systematic-debugging | Adapt | `systematic-debugging` | Same 4 phases and 3-strikes rule; strike 3 maps to BLOCKED/NEEDS DECISION; behavior-changing fixes re-route through Spec Kit |
| verification-before-completion | Adapt | `verifying-change` | Commands from the adapter; acceptance criteria from spec.md; mandatory in every lane |
| requesting-code-review, receiving-code-review | Adapt | `reviewing-change` (+ references) | Reviewer depth by lane; requirements = spec.md acceptance criteria; bounded fix loop |
| test-driven-development | Adapt | `test-driven-development` | Optional by default; `tdd: required` in the adapter makes it mandatory |
| finishing-a-development-branch | Adapt | `finishing-branch` | Same 3 options; PR body = DONE report |
| using-superpowers + SessionStart hook | Exclude | — | "Invoke a skill before ANY response" bootstrap competes with Spec Kit's entry point and causes ceremony on trivial work. The kit uses a short router block in `AGENTS.md` instead |
| writing-skills, diagnosing-superpowers | Exclude | — | Authoring and post-mortem tooling for Superpowers itself |
| `.superpowers/` workspaces, ledger scripts | Exclude | — | Assume Superpowers plan format; Spec Kit's `tasks.md` checkboxes are the progress record |

## Conflicts resolved

| Conflict | Resolution |
|---|---|
| Two planners (brainstorming→writing-plans vs. specify→plan→tasks) | Spec Kit is the only planner; `shaping-feature` ends at a brief |
| Two "spec" locations (`docs/superpowers/specs` vs. `specs/<feature>/spec.md`) | Only `specs/<feature>/`; briefs are optional history in `docs/briefs/` |
| Executor overrides the plan ("spec is binding, plan is its argument") | Small/local gaps → ruling; anything contradicting spec/plan → amend the artifact or NEEDS DECISION |
| Mandatory TDD everywhere | Adapter-controlled |
| "No check-ins" vs. human checkpoints | Kept: no check-ins, but exactly three handoff types |
| Verification at implement end (Spec Kit) vs. a separate skill | Upstream owns the loop; hooks own completion. Direct execution uses the same gates; unchanged evidence is reused |
