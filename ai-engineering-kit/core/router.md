## AI Engineering Kit

This project uses the AI Engineering Kit workflow (`.aiek/core/WORKFLOW.md`). Project facts and
commands are in `.aiek/adapter.md`.

For a new project with a BRD and no codebase: use `.aiek/core/WORKFLOW.md`'s New projects
path. Shape a Project Brief, run Spec Kit constitution and project roadmap, obtain explicit
roadmap approval, then classify and complete the first MVP slice. Do not classify the
whole project as one change.

For every change request (feature, bug, refactor) or approved roadmap slice:

1. **Discovery.** Arrived as a ticket with acceptance criteria → `intaking-ticket` first; it
   blocks on criteria nobody can check. Unclear *whether* to build it → `exploring-idea` skill
   → Idea Note → stop. Unclear *how* it should work → `shaping-feature` skill → Feature Brief
   → stop.
2. **Classify** the lane with `.aiek/core/classification.md` and state it in one line
   (`Lane: NORMAL (reason)`). Heavier lane when in doubt.
3. **Follow the lane:**
   - SMALL → `executing-task` → `verifying-change` → `reviewing-change` (self) → DONE
   - NORMAL → Spec Kit specify → (clarify) → plan → tasks → implement
   - LARGE → research → specify → clarify → plan → NEEDS DECISION if needed → tasks → analyze → implement (worktree, independent review)
   - INFRA (infrastructure, pipeline, deploy, release process, capacity) → recorded decision
     → `shipping-infrastructure` → `verifying-change` → independent review
     → `accepting-change` (ops)
4. Bugs start with `systematic-debugging`. Parallel work only via `parallel-development`.
5. Before reviewers look, `authoring-pr` writes the description from verification evidence.
   Before release, `accepting-change` runs the acceptance pass.

Rules:
- After `specify`, Spec Kit artifacts in `specs/<feature>/` are the only plan. Never write a
  second plan. Fix the artifact instead.
- No completion claim without fresh evidence (`verifying-change`). Always, every lane.
- Use BLOCKED, NEEDS DECISION or DONE for handoffs (`.aiek/core/handoffs.md`). Discovery
  questions and progress updates are allowed. Continue already-authorized steps.
- Do not activate a second planning/bootstrap workflow alongside this kit. Check globally
  installed skills/plugins too; project installation alone does not disable them.
- Project instructions in this file and in `.aiek/adapter.md` override kit defaults.
