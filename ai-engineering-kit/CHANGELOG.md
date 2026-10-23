# Changelog

All notable changes to the AI Engineering Kit. The version source is `manifest.json`;
`package.json` must match it (the build fails otherwise). Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-10-23

Phase 1 of the kit optimization plan: bring the 15 skills up to Agent Skills best practice and
add the capabilities Phase 2 needs (profiles, helper scripts, adapter contract v2, evals) without
creating a second workflow or planner. Backward compatible: `--profile full` remains the default,
adapter v1 keys still work, and every helper script is optional.

### Skills — triggering, format, progressive disclosure

- All 15 `skills/*/SKILL.md` descriptions rewritten to the same pattern: concrete `Use when`
  triggers, what the skill guarantees, and a `Not for` section naming the correct skill instead.
  Descriptions stay third-person, ASCII, at most 1024 characters.
- Near-miss disambiguation added where the old descriptions overlapped: `verifying-change` vs
  `reviewing-change` vs `accepting-change`, `executing-task` vs `test-driven-development`,
  `authoring-pr` vs `finishing-branch`, `exploring-idea` vs `shaping-feature` vs
  `intaking-ticket`, `shipping-infrastructure` vs `executing-task`.
- `## Gotchas` sections (concrete failure modes, 3–6 lines) added to `verifying-change`,
  `reviewing-change`, `executing-task`, `systematic-debugging` and `using-worktrees`.
- `test-driven-development` is now described as **adapter-controlled** rather than optional: the
  adapter/preset decides whether TDD is required, globally or for listed paths.
- Skill bodies kept at most 120 lines; long material stays in `references/`.
- Executing and verification skills document the optional helper scripts and the
  `verify.test_fast` (working loop) vs `verify.test_full` (final gate) split; `intaking-ticket`
  documents the traceability check. Manual fallbacks remain so the skills work without the
  scripts.
- The root `SKILL.md` was removed and replaced by `KIT.md`: a repository overview for humans with
  no frontmatter, never installed or discovered as a skill. A root `SKILL.md` was ambiguous
  because the installer copies the individual skills from `skills/`.

### Workflow correctness

- **PR ownership made explicit:** `authoring-pr` writes the PR/MR body from this session's
  verification evidence; `finishing-branch` chooses the disposition, reuses that body, and no
  skill opens, pushes or merges without an explicit request or the adapter's `integration`
  policy.
- **Risk-area semantics:** a `risk_areas` path forces the LARGE lane only when the change alters
  behavior, contract or operational procedure. Behavior-neutral edits inside a risk path do not
  become LARGE by themselves but still require human review when `review.human_required_for`
  names the path.
- **Planner selection:** `planning.mode` (`speckit | external | none`) is read by the router and
  by planning-aware skills; exactly one artifact set owns the plan in every mode.
- **Handoff language:** `output_language` now explicitly covers PR bodies, reports, acceptance
  sheets and user-facing prose, while commands, paths and IDs stay as written.
- **Documentation authority:** new `core/documentation.md` defines where each kind of fact lives
  (product/architecture docs, planner artifact, adapter, tracker, evidence) so plans never become
  a second set of docs. One fact, one owner; link, never copy.

### Adapter v2, install profiles, helper scripts

- Adapter contract v2 (all keys optional, v1 adapters keep working):
  - `planning.mode` with `plan_path` / `task_source` for external planners.
  - `repos` for multi-repository changes, plus `verify.run_fe`, `verify.ui` and explicit
    `verify.fe_*` frontend commands.
  - `verify.test_fast` and `verify.test_full` for the working loop and the final gate.
  - `baselines` (typed `file` / `command` / `prose` entries); the v1 `baseline` key is still
    accepted.
  - `worktree_name_pattern` and `branch_pattern` tokens `{repo}`, `{slug}`, `{ticket}`,
    `{feature}`, `{type}`.
  - Adapter `references/` and `scripts/` installed to `.aiek/adapter/references/` and
    `.aiek/adapter/scripts/`.
- `speckit-preset` samples for constitution, spec, plan and tasks templates; preset additions
  layer on (append to) the kit preset instead of replacing it.
- `scripts/install.sh`: `--profile core|discovery|full` (default `full`, backward compatible),
  `--only` and `--skip`. `core` installs the 11 execution/verification/integration skills;
  `discovery` installs the 4 discovery skills; `full` installs all 15.
- Four optional, stdlib-only Python helper scripts installed to `.aiek/scripts/`:
  `resolve_adapter.py` (read-only adapter command resolution), `verify.py` (run checks, write
  evidence, compare baseline, refuses deploy/merge/publish commands), `worktree.py` (isolated
  worktree using adapter patterns; no `--force`), `traceability.py` (acceptance-criteria
  traceability check). Each has `--help`, prints commands before running them, and is
  non-interactive.
- `.agents/skills/` is the canonical installed skills root; `.claude/skills/` is an optional
  mirror and the checker enforces parity when both are present.

### Evals and CI

- `evals/trigger.json` with 25 labeled queries (15 should-trigger, 10 near-miss negatives) and
  `scripts/eval_trigger.py`: majority-of-runs scoring, wrong-skill matrix, `--harness`,
  `--runs`, `--json`, `--mock`, exit nonzero below the threshold.
- 7 behavior fixtures in `evals/tasks/` with `scripts/eval_tasks.py`: Small, Normal, bug, vague
  ticket, review diff, infrastructure and parallel scenarios, with programmatic assertions for
  lane statements, artifacts, evidence tables, BLOCKED questions, findings and rollback plans.
- Harness-agnostic eval runs: **DeepSeek Harness (`dsh headless`) is the primary harness**;
  Claude Code and Codex are optional smoke harnesses; deterministic `--mock` mode runs in CI
  without credentials.
- `scripts/check_skills.py` validates skill metadata, body length and `.claude`/`.agents` parity;
  it runs from `scripts/check.sh` and against installed projects.
- CI workflow at the repository root (`.github/workflows/ai-engineering-kit.yml`, monorepo paths
  `ai-engineering-kit/**`): PR quick checks (static checks, tests, mock trigger/behavior evals)
  and a nightly full eval; no secrets required.
- Measured on 2026-10-23: trigger accuracy **23/25 = 92.0%** on the primary real harness
  (`dsh`, 25 queries x 3 runs, precision 100%) versus 20/25 = 80.0% at baseline; mock behaviour
  7/7 synthetic with 0 critical failures. The full real behaviour sample passed **3/7 (42.9%)**
  with **3 critical assertion failures** traced to eval-design/fixture gaps (no destructive or
  unsafe action was observed), so the behaviour gate is **not fully demonstrated**; real-harness
  behaviour remains the manual pre-release gate. Every limitation is listed in the eval report.
- Baseline and post-change reports: `docs/skills-baseline-2026-10-23.md` and
  `docs/eval-2026-10-23.md` (numbers copied from harness logs, including known limitations).
- Handover for Phase 2: `docs/phase-1-handover.md` (file map, measured results, decisions,
  residual risks, checklist).

### Docs and release

- README split: the local review UI, review flow, local data limits and Docs Copilot moved to
  `docs/local-review-ui.md`; the README keeps the overview, layout, install, harnesses, workflow,
  guide, principles and validation.
- `docs/huong-dan-workflow.md` (Vietnamese) updated: all 15 skills aligned with the final
  descriptions, install profiles, helper scripts, eval harness, adapter v2 keys and the
  documentation-authority pointer.
- `KIT.md` replaces the root `SKILL.md` as the repository overview; `package.json` `files` now
  ships `KIT.md` instead of `SKILL.md`.
- Plan docs updated: D4 = `.agents/skills/` canonical with optional `.claude/` mirror; D6 =
  DeepSeek Harness primary with Claude/Codex secondary and harness-agnostic scripts.
- Version bumped to 0.2.0 (`manifest.json` is the source, `package.json` and
  `package-lock.json` match).

### Compatibility

- Default install behaviour is unchanged: `--profile full`, same skill inventory (15).
- Adapter v1 key `baseline` still works; new adapter keys are optional and missing commands are
  discovered as before.
- Helper scripts are optional; skills keep manual fallbacks.
- `scripts/check.sh`, `scripts/test.py`, `scripts/test-speckit.py` and install dry-runs continue
  to pass.
