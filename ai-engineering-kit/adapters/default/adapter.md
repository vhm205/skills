---
adapter: default
default_branch: auto
verify:
  setup: auto
  test: auto
  lint: auto
  typecheck: auto
  build: auto
  e2e: null
  run: auto
tdd: optional
tdd_required_paths: []
worktree_dir: .worktrees
branch_pattern: "{feature}"
commit_policy: per-change
integration: ask
brief_dir: docs/briefs
risk_areas: []
review:
  human_required_for: []
tracker: none
---

# Default adapter

Used when a project has no adapter of its own. It knows nothing about the project, so it
**discovers** instead of assuming.

## `auto` commands

Every `auto` value is resolved with `.aiek/core/command-discovery.md`.

## Default conventions

- Match the style, structure and naming of the surrounding code.
- Do not add dependencies without a reason stated in the plan or the DONE report.
- Do not reformat files you did not otherwise change.
- Treat anything touching auth, payments, data migrations, secrets, or deployment as a hard
  trigger for the LARGE lane (see `.aiek/core/classification.md`), even with `risk_areas: []`.

## When to write a real adapter

As soon as a team uses the kit on a project more than a few times, copy
`adapters/_template/` and fill it in. Discovery costs tokens on every task. An adapter makes
it a lookup.
