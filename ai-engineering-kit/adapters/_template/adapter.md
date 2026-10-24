---
adapter: CHANGE-ME
default_branch: main

planning:
  mode: speckit            # speckit | external | none
  plan_path: null          # external mode only
  task_source: null        # external mode only

# repos:                   # optional, for multi-repo changes (name -> path)
#   be: .
#   fe: ../CHANGE-ME-fe

verify:
  setup: auto            # e.g. pnpm install && cp .env.example .env
  test: auto             # e.g. pnpm test
  test_fast: auto        # tight loop while executing (defaults to test)
  test_full: auto        # final gate (defaults to test)
  test_targeted: auto    # e.g. pnpm vitest run {path}
  lint: auto
  typecheck: auto
  build: auto
  e2e: null
  uat: null
  run: auto
  run_fe: null           # separate frontend, when repos.fe exists
  ui: null               # how/where to observe the UI
  fe_test: null          # explicit frontend checks
  fe_lint: null
  fe_typecheck: null
  fe_build: null

baselines: []            # known-accepted failures: [{name, kind: file|command|prose, value}]
# baseline: null         # v1 alias; prefer baselines

worktree_name_pattern: "{repo}-wt-{slug}"
worktree_dir: .worktrees
branch_pattern: "{type}/{slug}"   # tokens: {feature}, {slug}, {type}, {ticket}
commit_policy: per-task
integration: ask

output_language: null
pr_template: null
pr_required_sections: []

tdd: optional        # optional | required
tdd_required_paths: []
brief_dir: docs/briefs
risk_areas: []       # globs that force LARGE when behavior changes, e.g. "src/billing/**"
review:
  human_required_for: []

tracker: none        # none | github | plane | jira | linear
tracker_notes: ""

references: []       # adapter-relative docs copied to .aiek/adapter/references/
scripts: []          # adapter-relative helper scripts copied to .aiek/adapter/scripts/
---

# <Project> adapter

<!-- Short, imperative, project-specific rules. Link to longer docs rather than copying them.
     No secrets. No workflow changes. See .aiek/core/adapter-contract.md. -->

## Documentation map
- Product/roadmap docs: `<path>` — owns product intent, scope and phase order.
- Architecture/API docs: `<path>` — owns durable technical facts.
- QA/acceptance/evidence: `<path>` — owns checklists and evidence.
- Active planner: `specs/` (speckit) or `<external plan path>` (external).
<!-- One fact, one owner; link, never copy. See .aiek/core/documentation.md. -->

## Architecture boundaries
- <e.g. "UI never imports from server/; go through the API client">

## Conventions
- <naming, error handling, logging, i18n, etc.>

## Never
- <e.g. "never edit generated files under src/gen/; run `make gen`">

## Local running and observing
- <how to start the app, seed data, log in as a test user>

## Glossary
- <domain terms that appear in specs>
