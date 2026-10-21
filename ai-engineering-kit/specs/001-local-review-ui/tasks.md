# Tasks: Local Review UI

## Phase 1: Setup

- [x] T001 Add npm, TypeScript/Vite/lint/test setup and version validation in package.json, src/, ui/ and scripts/.
- [x] T002 Exclude generated/dependency trees in scripts/check.py and scripts/test.py, retain negative checks.

Checkpoint — Verify: build/typecheck, checker and Python installer tests.

## Phase 2: Feature reading (US1)

- [x] T003 [US1] Implement Markdown/source/task parser and safe project reader in src/ with tests/ fixtures.
- [x] T004 [US1] Implement authenticated loopback API, CLI and SSE watcher in src/; test auth, paths and refresh.
- [x] T005 [US1] Implement Vietnamese overview, decisions, tasks, evidence and source views in ui/.

Checkpoint — Verify: npm test; npm run build; browser source/live-refresh checks.

## Phase 3: Baselines (US2)

- [x] T006 [US2] Implement snapshot/diff storage in src/ and Changes view in ui/; test persistence, unseen edit conflicts and worktree separation.

Checkpoint — Verify: snapshot integration and browser tests.

## Phase 4: Editing (US3)

- [x] T007 [US3] Implement section editor, diff preview, guarded save and conflict recovery in src/ and ui/.

Checkpoint — Verify: byte preservation, stale/hash/path/token and browser tests.

## Phase 5: Packaging (US4)

- [x] T008 [US4] Test npm tarball launch, assets, ports, shutdown and runtime compatibility in tests/ and scripts/.
- [x] T009 Document quick start, storage, limitations and publication preparation in README.md.
- [x] T010 Run combined checks and independent review; resolve findings and record evidence in execution-log.md.

Checkpoint — Verify: npm run check; npm run test:e2e; npm run test:package; checker; installer dry-run; Python tests; independent review.

## Dependencies and execution

Execute T001–T010 sequentially. No [P] candidates: shared contracts and UI consume earlier outputs. MVP US1, then US2, then US3, package all stories in US4.
