---
adapter: CHANGE-ME
default_branch: main
verify:
  setup: auto            # e.g. pnpm install && cp .env.example .env
  test: auto             # e.g. pnpm test
  test_targeted: auto    # e.g. pnpm vitest run {path}
  lint: auto
  typecheck: auto
  build: auto
  e2e: null
  run: auto
tdd: optional        # optional | required
tdd_required_paths: []
worktree_dir: .worktrees
branch_pattern: "{feature}"
commit_policy: per-task
integration: ask
brief_dir: docs/briefs
risk_areas: []       # globs that force the LARGE lane, e.g. "src/billing/**"
review:
  human_required_for: []
tracker: none        # none | github | plane | jira | linear
tracker_notes: ""
---

# <Project> adapter

<!-- Short, imperative, project-specific rules. Link to longer docs rather than copying them.
     No secrets. No workflow changes. See .aiek/core/adapter-contract.md. -->

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
