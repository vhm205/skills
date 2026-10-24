---
adapter: default
default_branch: auto
planning:
  mode: speckit
  plan_path: null
  task_source: null
verify:
  setup: auto
  test: auto
  test_fast: auto
  test_full: auto
  lint: auto
  typecheck: auto
  build: auto
  e2e: null
  run: auto
baselines: []
worktree_name_pattern: "{repo}-wt-{slug}"
worktree_dir: .worktrees
branch_pattern: "{type}/{slug}"
commit_policy: per-change
integration: ask
output_language: null
tdd: optional
tdd_required_paths: []
brief_dir: docs/briefs
risk_areas: []
review:
  human_required_for: []
tracker: none
references: []
scripts: []
---

# Default adapter

Used when a project has no adapter of its own. It knows nothing about the project, so it
**discovers** instead of assuming.

## `auto` commands

Every `auto` value is resolved with `.aiek/core/command-discovery.md`. `test_fast` and
`test_full` default to the discovered `test` command when they cannot be discovered separately.

## Default conventions

- Match the style, structure and naming of the surrounding code.
- Do not add dependencies without a reason stated in the plan or the DONE report.
- Do not reformat files you did not otherwise change.
- Treat anything touching auth, payments, data migrations, secrets, or deployment as a hard
  trigger for the LARGE lane (see `.aiek/core/classification.md`), even with `risk_areas: []`.
- The planner is Spec Kit (`specs/<feature>/`) unless this adapter says otherwise. Do not
  create a second plan or a separate task list.

## When to write a real adapter

As soon as a team uses the kit on a project more than a few times, copy
`adapters/_template/` and fill it in. Discovery costs tokens on every task. An adapter makes
it a lookup.
