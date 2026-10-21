---
name: video-studio
description: Create and manage Vietnamese repo or article short videos through the local Moment Video Studio, including approval gates and targeted follow-up edits.
---

# Video Studio

Workspace: `/Users/moment/Projects/personal/lab/short-video`.
Canonical projects: `videos/draft/<slug>/revisions/<revision>/`. Published metadata remains in `videos/published/`.

Read [production contract](../references/production.md). Route repo requests to `repo-short`, article/news/note requests to `article-news-short`, and follow-up edits to `revise-video`. Vlog and avatar production are not supported by Studio v1; preserve the requested scope and explain the available legacy workflow.

## Chat entry

When `STUDIO_MANAGED_RUN` is not `1`, use `studio/.venv/bin/python studio/cli.py` from the workspace to create/manage the project. `new --title ... --kind repo|article --url ... --content-file ...` returns the project ID and URL. `run <id> script` queues the research/script phase. The CLI starts the local service if necessary. Return the Studio URL so the user can review. Do not start a parallel ad-hoc production or bypass Studio's approvals.

For a known project use `show <id>` before deciding what to do. A follow-up must identify the correct project and current revision; never assume the most recent global conversation is the target. Use `revise-video` for changes.

## Managed production

When `STUDIO_MANAGED_RUN=1`, you ARE the production agent. Do not call `cli.py new/run`, start another agent, or call Studio's mutation APIs. The runner prompt names your exact revision directory and phase boundary.

1. Read the workspace `AGENTS.md`, OpenMontage `AGENT_GUIDE.md` and the Studio `moment-short` manifest named by `brief.json.pipeline_type`. This custom manifest owns the short workflow gates; do not run the upstream long-form research/proposal/executive-producer stages. Load technical director references only when their stage is active.
2. Load `brief.json`; production choices there are user-selected defaults. Present proposal and storyboard together in the script gate. Never forge approval checkpoints; set gated checkpoints to awaiting_human and stop when the current phase ends.
3. Before writing a script, run `python3 scripts/check_duplicate.py '<repo name or topic>'` from the workspace. Review related published angles and the brief's selected angle.
4. Use source evidence and official documentation, and keep stable scene and section IDs.
5. Write canonical OpenMontage artifacts and the phase completion artifact specified in [artifact contract](../references/artifacts.md).
6. Stop at the requested phase. Missing source, unavailable voice/runtime, payment requirement or a quality failure is a blocker; preserve completed work and state the next action.

Never publish, schedule, delete heavy assets, change provider, or call a paid generator from a managed production phase. Publishing is controlled separately by an explicit release/schedule approval.
