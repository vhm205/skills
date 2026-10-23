# Adding a Project Adapter (e.g. Plane, Orchexa)

An adapter teaches the kit one project's facts: commands, risky areas, review rules, planning
mode, tracker. It never changes the workflow. Contract:
[`core/adapter-contract.md`](../core/adapter-contract.md). Fact ownership:
[`core/documentation.md`](../core/documentation.md).

## 1. Create it

```bash
cp -R adapters/_template adapters/plane
```

Or keep the adapter **in the project repo** (recommended once it stabilizes) and pass its path
to the installer. The kit then stays free of project details.

## 2. Fill in `adapter.md`

Work from the project's real sources (CI config, Makefile, package.json, CONTRIBUTING):

```yaml
---
adapter: plane
default_branch: preview

planning:
  mode: speckit              # speckit (default) | external | none
  plan_path: null            # external: where the plan lives
  task_source: null          # external: where the tasks live

repos:                       # optional, for a BE/FE split
  be: .
  fe: ../plane-fe

verify:
  setup: pnpm install
  test: pnpm turbo run test
  test_fast: pnpm turbo run test --filter=api
  test_full: pnpm turbo run test
  lint: pnpm turbo run check:lint
  typecheck: pnpm turbo run check:types
  build: pnpm turbo run build
  run: pnpm dev
  run_fe: pnpm dev --filter=web
  ui: http://localhost:3000
baselines:
  - name: unit
    kind: file
    value: docs/qa/baseline-unit.txt
worktree_name_pattern: "{repo}-wt-{slug}"
branch_pattern: "{type}/{slug}-{ticket}"
risk_areas: ["apps/api/plane/db/migrations/**", "apps/api/plane/authentication/**"]
review:
  human_required_for: ["apps/api/plane/authentication/**"]
tracker: plane
tracker_notes: "Reference the work item ID in the branch name and PR title."
---
```

_(Commands above are illustrative; verify each one against the project before relying on it.)_

Then add short prose: documentation map, architecture boundaries, conventions, "never" rules,
how to run locally, glossary. Link to existing docs instead of copying them.

### Which planning mode?

- `speckit` — the project uses Spec Kit; `specs/<feature>/` owns the plan and tasks.
- `external` — the project plans in its own documents (for example a docs-based plan folder).
  Set `planning.plan_path` and `planning.task_source`; execution skills read those and never
  create `specs/`.
- `none` — no planning artifacts; only Small/infra work is allowed.

Never run two planners for the same work. See [`core/documentation.md`](../core/documentation.md)
for which document owns which fact.

## 3. Optional: Spec Kit customization

If the project needs extra spec/plan/tasks sections or a project constitution section, edit
`adapters/<name>/speckit-preset/`. It is installed with priority 5, ahead of the kit preset
(10). The template includes `spec-template.md`, `plan-template.md`, `tasks-template.md` and
`constitution-template.md` samples; keep additions short and link to project docs instead of
copying them. Appended spec/plan/tasks sections are composed immediately after
`specify preset add` (verify with `specify preset resolve spec-template`). Constitution
additions are resolved by the `/constitution` command when it regenerates the file; an already
authored `constitution.md` is never overwritten — install the `constitution-sync` preset if the
team wants a reviewed snapshot.

Durable engineering *principles* belong in the project's
`.specify/memory/constitution.md` (run Spec Kit `constitution`), not in the adapter. Commands
and paths belong in the adapter.

## 4. Optional: adapter references and scripts

The adapter directory may contain:

```text
adapters/<name>/
├─ references/         # docs installed to .aiek/adapter/references/
└─ scripts/            # helper scripts installed to .aiek/adapter/scripts/
```

List them in frontmatter (`references: [references/runbook.md]`,
`scripts: [scripts/seed.sh]`) so the installer copies them and the skills can link to stable
`.aiek/adapter/...` paths.

## 5. Install into the project

```bash
cd /path/to/project
specify init --here --integration codex         # or claude, agy, ... (once per project)
/path/to/ai-engineering-kit/scripts/install.sh . --adapter plane --speckit
# adapter kept in the project repo instead:
/path/to/ai-engineering-kit/scripts/install.sh . --adapter ./tools/aiek-adapter --speckit
```

Install profile options:

```bash
scripts/install.sh . --profile core        # 11 execution/verification/integration skills
scripts/install.sh . --profile discovery   # 4 discovery skills only
scripts/install.sh . --profile full        # all 15 (default, backward compatible)
scripts/install.sh . --profile core --only verifying-change,authoring-pr
scripts/install.sh . --profile full --skip parallel-development
```

The installer also copies the helper scripts to `.aiek/scripts/`:
`resolve_adapter.py`, `verify.py`, `worktree.py`, `traceability.py` (Python 3, standard
library only; `--help` on each).

- `resolve_adapter.py --repo . --json` — resolved adapter commands, read-only.
- `verify.py --adapter .aiek/adapter.md --scope changed --only test,lint --dry-run` — prints
  and runs the matching checks, writes evidence.
- `worktree.py --adapter .aiek/adapter.md --slug my-change --ticket OSA-123 --setup` — creates
  an isolated worktree using the adapter's patterns.
- `traceability.py --file specs/007-my-change/spec.md` — checks each acceptance criterion has a
  traceability row and proof.

## 6. Check it

- `.aiek/adapter.md` is the project's adapter
- Ask the agent: "Classify this change: <real example>". It should name the lane and cite the adapter's risk areas.
- Ask for a Small change and confirm DONE quotes the adapter's commands with real output.
- Run `python3 scripts/check_skills.py . --kit /path/to/ai-engineering-kit` to verify installed
  skills, and `python3 .aiek/scripts/resolve_adapter.py --repo . --json` to confirm the adapter
  parses.

## Rules of thumb

- An adapter can raise rigor (risk areas, required TDD, human review), never lower it. Risk
  areas only force LARGE when the change alters behavior, contract or operational procedure.
- No secrets; refer to env var names.
- Keep the prose under ~150 lines. If it grows, link out.
- Re-running `install.sh` never overwrites `.aiek/adapter.md` unless you pass `--force`.
- New keys are optional and backward compatible; a v1 adapter keeps working.
