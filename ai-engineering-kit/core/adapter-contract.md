# Adapter Contract

The kit's core and skills are project-agnostic. Everything that differs between projects —
commands, conventions, risk areas, tracker, planning mode, review rules — lives in an
**adapter**.

In a project that installed the kit, the active adapter is a single file:
`.aiek/adapter.md`. Skills read it; they never hard-code project facts.

## Layout of an adapter in this kit

```text
adapters/<name>/
├─ adapter.md              # required: YAML frontmatter (machine-readable) + prose conventions
├─ speckit-preset/         # optional: a Spec Kit preset with project-specific overrides
│  ├─ preset.yml           #   constitution/spec/plan/tasks template additions
│  └─ ...
├─ references/             # optional: project docs the installer copies to .aiek/adapter/references/
├─ scripts/                # optional: project helper scripts copied to .aiek/adapter/scripts/
└─ README.md               # optional: what this adapter is for
```

The installer copies `references/` and `scripts/` into `.aiek/adapter/` when present and lists
them in the install output. Keep secrets out of them.

## `adapter.md` frontmatter

All keys are optional. A missing key, or the value `auto`, is resolved with
[command-discovery.md](command-discovery.md) where a command is expected. There is no adapter
inheritance: the agent reads one file, so put every non-default value in it.

```yaml
---
adapter: my-project          # name
default_branch: main         # or "auto" (detect from origin/HEAD)

planning:                    # which artifact is the one plan; see documentation.md
  mode: speckit              # speckit | external | none (default: speckit)
  plan_path: null            # external: path to the plan document
  task_source: null          # external: path to the task list/queue

repos:                       # optional multi-repo map, name -> path (relative to this repo)
  be: .
  fe: ../my-project-fe       # omit when the project is one repo

verify:                      # used by verifying-change, using-worktrees, executing-task
  setup: pnpm install        # dependency/bootstrap step for a fresh worktree
  test: pnpm test            # default/combined check
  test_fast: pnpm test -w    # optional: tight loop while executing
  test_full: pnpm test       # optional: final gate (defaults to test)
  test_targeted: pnpm test -- {path}   # optional; {path} is replaced
  lint: pnpm lint
  typecheck: pnpm typecheck
  build: pnpm build
  e2e: null                  # null = not available; say so in DONE
  uat: null                  # full scenario/acceptance suite, for accepting-change
  deploy_check: null         # proves a deployed environment is in the intended state
  run: pnpm dev              # how to observe the app, for UI verification
  run_fe: null               # how to run a separate frontend, when repos.fe exists
  ui: null                   # how/where to observe the UI (URL, storybook, screenshot cmd)
  fe_test: null              # explicit frontend checks, when commands cannot be inferred
  fe_lint: null
  fe_typecheck: null
  fe_build: null

baselines:                   # known-accepted failures; see below
  - name: unit
    kind: file              # file | command | prose
    value: docs/qa/baseline-unit.txt
  - name: e2e
    kind: prose
    value: "3 checkout tests fail on main since 2026-10-01; tracked in OSA-42"
# baseline: path-or-prose is the v1 alias; prefer baselines.

worktree_name_pattern: "{repo}-wt-{slug}"   # tokens: {repo}, {slug}, {ticket}, {feature}
worktree_dir: .worktrees
branch_pattern: "{type}/{slug}"  # tokens: {feature}, {slug}, {type}, {ticket}
commit_policy: per-task      # per-task | per-change | manual
integration: ask             # ask | pr | merge (finishing-branch default; "ask" recommended)

output_language: null        # language for PR bodies, reports, acceptance sheets
pr_template: null            # path to the project's PR template; null = kit default sections
pr_required_sections: []     # section titles authoring-pr must not leave out

tdd: optional                # optional | required
tdd_required_paths: []       # globs where TDD is required even if tdd: optional

brief_dir: docs/briefs       # where shaping-feature saves briefs when asked to persist

risk_areas:                  # touching these FORCES the LARGE lane when behavior changes
  - "src/auth/**"
  - "migrations/**"
review:
  human_required_for: []     # globs/areas that always need a human reviewer

tracker: none                # none | github | plane | jira | linear | ...
tracker_notes: ""            # how tasks map to tickets, if at all

references: []               # adapter-relative doc paths copied to .aiek/adapter/references/
scripts: []                  # adapter-relative helper scripts copied to .aiek/adapter/scripts/
---
```

## Planning mode

`planning.mode` tells every planning-aware skill which artifact is authoritative:

| Mode | One plan lives in | Use when |
|---|---|---|
| `speckit` (default) | `specs/<feature>/spec.md`, `plan.md`, `tasks.md` | The project uses Spec Kit |
| `external` | `planning.plan_path` (plan) and `planning.task_source` (tasks) | The project has its own planning system (e.g. docs-based plans) |
| `none` | No plan artifacts; Small/infra changes only | The project explicitly does not use planning artifacts |

In `external` mode, execution skills read the named files, never create `specs/`, and never
create a second plan. `speckit-preset` is irrelevant in that mode. See
[documentation.md](documentation.md) for the full fact-ownership model.

## `baselines`

A project with known, accepted failures lists them under `baselines`. "Green" then means
*no failures beyond the baseline*, not zero failures, for `verifying-change` and
`test-driven-development`. Each entry says whether it is machine-readable (`kind: file`), a
reproducible command (`kind: command`), or prose a person must read (`kind: prose`), because
they cost very different amounts of attention. A baseline may shrink. It may never be widened
to absorb a new failure.

The v1 key `baseline: <path-or-prose>` is still accepted; new adapters should use `baselines`.

## Repositories

For a change that spans repositories, list them under `repos` (`name: path`). Paths resolve
from the repo root; `.` is the current repo. `verify.*` commands run in the primary repo;
`verify.fe_*` and `verify.run_fe` describe the frontend when it is separate. Worktrees get one
checkout per repo involved, named with `worktree_name_pattern`.

## Prose section

Below the frontmatter, write short, imperative project rules the skills should respect:
code style, architecture boundaries, naming, "never do X" rules, how to run things locally,
domain glossary, and where the project's docs live. Keep it under ~150 lines. Link to longer
project docs instead of copying them.

## Rules for adapters

1. **No workflow changes.** Adapters configure the canonical workflow; they do not add
   stages, rename handoffs, or introduce a second planning artifact.
2. **Risk can only go up, and only for behavior.** An adapter may add `risk_areas`, require
   TDD, or require human review; it may not exempt changes from verification. A purely
   behavior-neutral edit inside a `risk_areas` path (typo, comment, formatting) does not
   become LARGE by itself, but still needs a human reviewer when `review.human_required_for`
   names that path.
3. **Routing is allowed; redefining stages is not.** An adapter may say "symptom X is already
   covered by the project's own playbook Y" and send the agent there. It may not add a stage,
   rename a handoff, or introduce a second planning artifact.
4. **Spec Kit customization goes through a preset.** Project-specific spec/plan/tasks
   template changes or a constitution template belong in `speckit-preset/`, installed with a
   lower priority number (= higher precedence) than the kit preset.
5. **Secrets never go in an adapter.** Reference env var names, not values.
6. **Backward compatible.** New keys are optional. Adapters written for v1 keep working: a
   missing `planning` behaves like `speckit`, missing baselines/tokens use defaults, and a
   missing command is discovered rather than invented.

## Spec Kit constitution vs. adapter

- `.specify/memory/constitution.md`: durable engineering *principles* the spec/plan must
  satisfy (e.g. "library-first", "every API change is versioned"). Owned by Spec Kit.
- `.aiek/adapter.md`: operational *facts and commands* (how to test, where risky code lives).

If a rule is a principle the plan must be checked against, put it in the constitution.
If it is a command or a path, put it in the adapter. If it says which document owns which
fact, it belongs in [documentation.md](documentation.md) plus the adapter's prose paths.
