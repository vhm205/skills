---
adapter: orchexa
default_branch: staging
verify:
  setup: cd bridge && python -m venv .venv && ./.venv/bin/pip install -e . pytest pytest-asyncio
  test: bash scripts/e2e-report.sh
  test_targeted: cd bridge && .venv/bin/python -m pytest {path} -q -o addopts=
  lint: cd bridge && .venv/bin/ruff check {path}
  typecheck: null
  build: null
  e2e: npx playwright test
  uat: bash scripts/uat-scenarios.sh
  deploy_check: bash scripts/staging-deploy-check.sh
  run: cd docker && docker compose -f docker-compose.core.yml up -d --build
baseline: docs/ONBOARDING/05-dev-vao-viec.md
tdd: required
tdd_required_paths: []
worktree_dir: ../
branch_pattern: "{type}/{slug}"
commit_policy: per-change
integration: ask
brief_dir: .planning/
output_language: vi
pr_template: null
pr_required_sections:
  - "Release note"
  - "Production .env setup"
risk_areas:
  - "migrations/**"
  - "bridge/app/billing/**"
  - "bridge/app/mcp_auth/**"
  - "bridge/app/security/**"
  - "bridge/app/middleware/**"
  - "bridge/app/services/llm_gateway.py"
  - "bridge/app/services/reply_finalizer.py"
  - "bridge/app/prompts/composer.py"
  - "bridge/app/services/journey/**"
  - "k8s/**"
  - "scripts/deploy-prod.sh"
  - "scripts/build-push-bridge.sh"
  - "scripts/e2e-report.sh"
  - ".github/workflows/**"
review:
  human_required_for:
    - "migrations/**"
    - "k8s/**"
    - "bridge/app/billing/**"
    - "bridge/app/security/**"
tracker: plane
tracker_notes: "Tickets are OSA-NNN on the Plane instance. Bug rows from QA use BUG-NNN, a separate continuing sequence that appears in test filenames and PR titles."
---

# Orchexa adapter

Two repositories checked out side by side on the same branch name: `orchexa-be` (Python 3.12 /
FastAPI monolith under `bridge/`, plus `services/`) and `orchexa-fe` (Next.js dashboard and the
widget SDK). Commands run from the `orchexa-be` root. Paths below are as they exist on
`staging`; a feature branch may not carry all of them.

## Where the real process lives — read these, they are not restated here

| Stage | Document |
|---|---|
| Lifecycle: 7 phases, 4 gates | `docs-e2e/QA-SDLC-WORKFLOW.md` |
| Daily agreement: test lanes, TDD rules, migrations, parallel clusters | `docs/ONBOARDING/05-dev-vao-viec.md` |
| **Silent-failure doctrine and the traps below, in full** | `CLAUDE.md` §"BA HỌ LỖI IM LẶNG" |
| Commit subject and release-note conventions | `CLAUDE.md` §"Product changelog convention" |
| Bug intake: the 9 required columns | `docs-e2e/BUG-REPORT-TEMPLATE.md` |
| Ready / Done checklists | `docs-e2e/QA-SIGNOFF-PLAYBOOK.md` §1 |
| Test layers and the coverage report | skill `orchexa-testing-unit-integration-behaviral-test` |
| Deploy checklist | `docs/deploy/PROD-DEPLOY-CHECKLIST.md` |
| Journey / Edupia work | `CLAUDE-Edupia.md` — read **before** touching journey, automation, conversation or CRM sync |

Kit lanes map onto that lifecycle: `intaking-ticket` = Gate 0, `verifying-change` = Gate 1,
`accepting-change` = Gates 1b and 2.

## Test layers — pick the lowest that proves the behavior

| Behavior | Lives in |
|---|---|
| Pure logic: validate, parse, resolve, merge | `bridge/tests/pure/` |
| SQL, service or endpoint touching the database | `bridge/tests/integration/` |
| Dashboard / SDK return values | `orchexa-fe/src/__tests__/` |
| Widget runtime DOM | `orchexa-fe/e2e-sdk/` |
| React component layout (real CSS) | `orchexa-fe/e2e-ui/` |
| Model output | skill `e2e-agent-test` |

Naming: `tests/pure/test_bugNNN_<slug>_<date>.py`, paired with
`tests/integration/test_bugNNN_<slug>_db.py` when there is SQL.

Integration tests are opt-in: `eval "$(scripts/test-db.sh)"` provisions a throwaway Postgres and
exports `RUN_DB_TESTS=1`. A faster dockerised lane and its traps are in
`docs/ONBOARDING/05-dev-vao-viec.md` §3.

**Every new SQL statement needs a test that runs it against real Postgres.** The pure suite uses
a fake database and never parses SQL, so a broken query there is a silent no-op.

## What "green" means here

No failures **beyond the accepted baseline**, not zero failures.

- Backend baseline is **prose**, in `docs/ONBOARDING/05-dev-vao-viec.md` §3 (roughly 1 pure,
  18–22 integration, 7 frontend files). Read it and compare by hand; state in the report which
  reds you matched against it.
- Frontend baseline is a file: `scripts/fe-vitest-baseline.txt`, checked by
  `python3 scripts/check_fe_vitest_baseline.py <junit.xml>`.
- `baselines/embedded-ai-baseline-20260701.json` is unrelated to test reds.

A red outside the baseline is a regression. Never weaken an assertion to reach green.

## Five traps, each already paid for

1. **The CI gate runs a file list, not a directory.** `scripts/e2e-report.sh` holds a
   `BE_MAIN_FILES` array of ~546 paths. A new test not added to it never runs and the gate still
   reports green — the hole an independent review caught on PR #206. Add the file, then confirm
   it appears in the run.
2. **A patch that exists is not a patch that is running.** Core stack does **not** bind-mount:
   rebuild `bridge-core worker-core worker-journey-core`. Legacy `sip-ai-bridge` bind-mounts but
   has no `--reload`: `docker restart sip-ai-bridge`. **Never verify with
   `docker exec … python -c "import app"`** — a new process always agrees with you; compare
   `docker inspect -f '{{.State.StartedAt}}'` against file mtime. Build with
   `--build-arg BUILD_SHA=$(git rev-parse --short=9 HEAD)`. The vector index is its own
   artifact. Full doctrine: `CLAUDE.md` §"BA HỌ LỖI IM LẶNG".
3. **One copy of the SDK is real:** `orchexa-fe/public/sdk/voice-agent.js`. The copies under
   `orchexa-be/bridge/sdk/`, `orchexa-be/sdk/web/` and `orchexa-fe/out/sdk/` are traps. After
   editing, bump `?v=` in **both** script-tag callers.
4. **Migrations** are flat `migrations/NNN_description.sql` at the repo root, applied at bridge
   and worker startup, keyed on **filename** — renaming an applied file makes production rerun
   it. A name not matching `^\d{3,}_[a-z0-9_]+\.sql$` is **skipped silently**. No ORM, no
   Alembic. Split number ranges when working in parallel.
5. **Lint and typecheck are not gates, and neither runs clean** (measured 2026-10-22):
   `ruff check app` exits 1 with **14,934 pre-existing errors**, so lint only the files you
   changed and say so; `mypy` **cannot run at all** — `mypy app` exits 2 on
   `Duplicate module named "middleware" (also at "app/api/middleware.py")` and checks nothing,
   hence `typecheck: null`. Do not claim a clean typecheck.

## Chokepoints enforced by sentinel tests

Bypassing any of these turns a test red and blocks merge: every provider call through
`services/llm_gateway.py` `gw.call()`; every customer-facing answer through
`services/reply_finalizer.py` `finalize()`; no model name outside `config.py`,
`model_allowlist.py`, `tier_service.py` and the catalogs in
`tests/pure/test_llm_flows_bam_env.py`; no provider credential via `os.getenv` outside
`config.py`; no customer name anywhere in `bridge/app/**`, comments included.

## Route a symptom to the playbook that already exists

All under `.claude/skills/`. Check here before investigating from scratch.

| Symptom | Skill |
|---|---|
| Journey/automation chain did not run, event never arrived, customer stuck, CRM body empty | `orchexa-edupia-trace-root-cause-from-profile` — run its `scripts/tom_tat.py` on the trace export; never `Read` that JSON |
| Answer content wrong, tools not called, intent misclassified | `widget-chat-debug` |
| Product carousel or image did not render | `orchexa-debug-widget-product-carousel` |
| Reply slow or hanging | `orchexa-diagnose-chat-latency` |
| Handover to a human misbehaves | `escalation-debug` |
| Facebook / Instagram / Zalo | `orchexa-debug-meta-fb-ig-integration` |
| Planner vs ReAct mode | `orchexa-debug-agent-planner-mode` |
| Voice, audio, transcript | `orchexa-debug-voice-widget` |
| Why the agent answered a given way | `agent-diagnostic` |
| Writing the tests and the coverage matrix | `orchexa-testing-unit-integration-behaviral-test` |
| Model-output acceptance on staging | `e2e-agent-test` |

Tracing is self-hosted Langfuse. Trace ids live in `chat_messages.metadata->>'trace_id'`; fetch
one via `GET /api/v1/conversations/{conversation_id}/messages/{message_id}/trace` (superadmin).

## Parallel work

`using-worktrees` and `parallel-development` follow the project's cluster procedure
(`docs/ONBOARDING/05-dev-vao-viec.md` §7, run ~92 times), not the kit defaults. The parts most
often skipped: the sub-agent's brief must name **the hard cases it must cover**, the current red
baseline and its **migration number range**; a sub-agent **does not push, merge or open a PR**;
the main agent merges, runs **all three lanes**, compares the baseline, updates the tracker,
then pushes. Two or three clusters at once, no more. **Never resolve a conflict with a union
script.** If an agent dies, take over its worktree rather than restarting.

## Infrastructure lane (module M10)

Manifests `k8s/base/` + `k8s/overlays/{dev,production}/` (kustomize). Build and publish
`scripts/build-push-bridge.sh` — always pass the build-sha argument above. Deploy
`scripts/deploy-prod.sh`; verify `scripts/staging-deploy-check.sh`. Checklist
`docs/deploy/PROD-DEPLOY-CHECKLIST.md`. Workflows not yet enabled sit in
`docs/ci-workflows-pending/`. Note that `staging-api.orchexa.io` tunnels to a local container,
so local **is** staging for the legacy stack — confirm which stack you are looking at.

Never push an image to a shared registry, cut over an environment, or migrate a shared or
production database without asking first.

## Pull requests and commits

```
[OSA-NNN] <type>(<area>): một câu khách đọc được
```

The subject **is** the public changelog line: Vietnamese, outcome not implementation.
Customer-visible types `feat` `fix` `perf` `revert`; hidden `refactor` `chore` `ci` `docs`
`test` `build` `style`. `area` ∈ `widget-chat` `playground` `zalo-user` `zalo-oa` `facebook`
`instagram` `whatsapp` `telegram` `rag` `crm` `tracing` `admin` `analytics` `voice` `api`
`integrations` `billing` `onboarding`. Branches in use: `osa-NNN-<name>-<hash>`,
`feature/OSA-NNN-<slug>`, `fix/bug-NNN-<slug>`. Base is `staging`.

There is **no** `.github/PULL_REQUEST_TEMPLATE.md`, so `authoring-pr` uses the kit's default
sections. Both required sections are `CLAUDE.md` rules: a `## Release note` with the exact
public sentence, and a `## Production .env setup` listing keys to add and remove whenever the
diff reads a new `os.getenv` — names only, never values. Title the kit's "Configuration
changes" section `## Production .env setup` rather than adding a second one. Body in
Vietnamese; PR #206 is the worked example. Checked 2026-10-22: the kit's defaults cover 13 of
PR #206's 14 headings; the missing one is its optional collapsed appendix of review reports.

For prose a person reads — business goal, overview, release note — run a rewrite pass
(`agy -p`, falling back to `codex exec`), then compare numbers, identifiers and terminology
against the original before posting.

## Trackers

Plane (`tracker.orchexa.io`) owns tickets. The in-repo tracker is
`docs/unicorn-saas-plan/tracker/state.json`: edit it, run `scripts/unicorn_tracker.py`, commit
both — `tests/pure/test_tracker_dong_bo.py` gates the pair. `done` there means *measured*. A gap
that is not a single-screen bug gets a `GAP-*` entry at the moment of discovery, titled by its
user-visible consequence.

## Dormant — do not use

`.agent/` holds ~40 vendored skills and 11 workflows from another framework, one commit from
2026-01-26, referenced by nothing live. It contains look-alikes named `tdd-workflow`,
`systematic-debugging`, `brainstorming` and `plan-writing`: running them alongside this kit is
the second competing workflow `.aiek/core/WORKFLOW.md` forbids. `.beads/` and `.collaborator/`
are inert too. `orchexa-fe/CLAUDE.md` §"Skill routing" lists twelve skills that do not exist in
that repository — ignore that table.
