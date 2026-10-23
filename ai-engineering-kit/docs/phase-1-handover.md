# Phase 1 Handover — AI Engineering Kit 0.2.0

**Branch:** `feat/phase-1-kit-optimization` · **Date:** 2026-10-23
**Scope:** Phase 1 of [Plan 2 Phase](plan-2-phases-2026-10-23/README.md), limited to
`ai-engineering-kit/`. Phase 2 (Orchexa + Spec Kit integration) is not started.
**Status:** implemented on branch `feat/phase-1-kit-optimization`; **trigger gate passed** on the
primary real harness (`dsh`, 23/25 = 92.0%); **behaviour gate not fully demonstrated** (real `dsh`
full run 3/7 = 42.9% with 3 critical assertion failures; the mock 7/7 is synthetic
assertion-engine evidence only) — a documented limitation, see §4.3 and §6. This is not a claim
that the full Phase 1 DoD passed. This document is the T33 deliverable.

---

## 1. What changed

Version 0.1.0 → **0.2.0**. See [CHANGELOG.md](../CHANGELOG.md) for the grouped list. In one
paragraph: all 15 skill descriptions were rewritten around explicit triggers and exclusions,
five gotcha sections and the TDD "adapter-controlled" wording were added, the root `SKILL.md`
became the non-installed `KIT.md`, workflow contradictions around PR ownership, risk-area
semantics and planner selection were resolved, the adapter contract advanced to v2 with
`planning`, `repos`, `test_fast`/`test_full`, typed `baselines` and pattern tokens, the installer
gained `core` / `discovery` / `full` profiles and four optional helper scripts, and the kit now
has a harness-agnostic trigger/behavior eval harness with CI.

Nothing in Orchexa was touched (Phase 1 boundary). Measured gates: trigger PASS on the real
harness, behaviour NOT demonstrated by the real sample (documented gap — §4.3).

---

## 2. Decisions recorded

| # | Decision | Resolution |
|---|---|---|
| D4 | Canonical skills root: `.agents` or `.claude`? | **`.agents/skills/` is canonical.** `.claude/skills/` is an optional mirror; when both are installed the checker enforces parity. |
| D6 | Primary eval harness | **DeepSeek Harness (`dsh headless`) is primary.** Claude Code and Codex are optional smoke harnesses; the eval scripts are harness-agnostic (`--harness dsh\|claude\|codex\|mock`) so CI runs deterministic `--mock` without credentials. |
| T07 | Root `SKILL.md` or `KIT.md`? | **`KIT.md`**, a human overview with no frontmatter, not installed. Rationale in `KIT.md` and README: the installer copies individual skills, so a root meta-skill was ambiguous. |
| T08 | Dependency declaration for skills | Frontmatter stays strictly `name` + `description` (open Agent Skills fields only). Installed skills depend on `.aiek/core/*.md` + `.aiek/adapter.md` written by `install.sh`; if `.aiek/` is missing, re-run the installer. Documented in README. |

Other decisions from the plan (D1, D2, D3, D5, D7) belong to Phase 2 and were not needed for
Phase 1.

---

## 3. File map

| Area | Files | Change |
|---|---|---|
| Skills | `skills/*/SKILL.md` (15) | Trigger/exclusion descriptions, gotchas, TDD wording, script + manual fallbacks |
| Root entry | `KIT.md` (new), `SKILL.md` (deleted) | Repo overview replaces the ambiguous root skill |
| Core | `core/WORKFLOW.md`, `classification.md`, `handoffs.md`, `router.md`, `adapter-contract.md`, `documentation.md` (new) | PR ownership, risk semantics, planner selection, report language, adapter v2, fact ownership |
| Adapters | `adapters/_template/`, `adapters/default/`, `adapters/_template/speckit-preset/` | v2 template keys, docs map, preset samples (constitution/spec/plan/tasks). `adapters/orchexa/` is unchanged: Phase 1 does not touch Orchexa. |
| Installer | `scripts/install.sh`, `manifest.json` | Profiles `core\|discovery\|full`, `--only`, `--skip`, install `.aiek/scripts/` and adapter refs |
| Helper scripts | `scripts/resolve_adapter.py`, `verify.py`, `worktree.py`, `traceability.py` (new), `scripts/check_skills.py` (new) | Phase 2 enablers; static checker for skills/parity |
| Tests | `scripts/test.py`, `scripts/test_scripts.py` (new), `scripts/test-speckit.py`, `scripts/check.sh` | Profile/script coverage; checker wired into `check.sh` |
| Evals | `evals/trigger.json`, `evals/tasks/`, `scripts/eval_trigger.py`, `scripts/eval_tasks.py`, `docs/skills-baseline-2026-10-23.md`, `docs/eval-2026-10-23.md` | Harness-agnostic trigger + behavior evals, baseline and post-change reports |
| CI | repo root `.github/workflows/ai-engineering-kit.yml` | PR quick checks + nightly full eval for the monorepo path `ai-engineering-kit/**`, no secrets |
| Docs/release | `README.md`, `docs/huong-dan-workflow.md`, `docs/local-review-ui.md` (new), `docs/adding-an-adapter.md`, `AGENTS.md`, `CHANGELOG.md` (new), plan docs | README split, Vietnamese guide, adapter guide, changelog, version, plan decisions |

Not changed: `speckit/` command logic, workflow stages, handoff format, skill ownership.

---

## 4. Measured results

> Numbers in this section are copied from the eval report, never estimated. Primary source:
> [`docs/eval-2026-10-23.md`](eval-2026-10-23.md); pre-change baseline:
> [`docs/skills-baseline-2026-10-23.md`](skills-baseline-2026-10-23.md). Both reports state
> exactly what was run and what could not be run.

Numbers below are copied from the eval report and corroborated against the machine-readable
result files in `evals/results/`; nothing here is estimated. Mock-mode numbers are labelled as
such and are never presented as model evidence.

### 4.1 Static skill metrics — baseline vs branch

Measured by `evals/measure_baseline.py` against an immutable `main@85f27c7` snapshot:

| Metric | Baseline (`main@85f27c7`) | Branch | Target |
|---|---:|---:|---|
| Skills | 15 | 15 | 15 |
| Descriptions with literal `Use when` | 0/15 | **15/15** | 15/15 |
| Descriptions with a negative trigger | 5/15 | **15/15** | 15/15 |
| Descriptions with quoted trigger examples | 0/15 | **15/15** | — |
| Description chars (total) | 3,632 | 9,535 | each ≤ 1,024 |
| Body lines (total) | 1,059 | 1,163 | each ≤ 120 |
| Reference files | 13 | 13 | — |
| Evals present | no | **yes** (25 queries, 7 fixtures, 2 runners) | yes |

### 4.2 Trigger eval — real DeepSeek Harness (primary)

Command: `python3 scripts/eval_trigger.py --harness dsh --runs 3 --kit-label current-branch`
(25 queries × 3 runs, majority; skill use read from actual `skill` tool-call events):

| Metric | Baseline `dsh` (1 run/query) | Branch `dsh` (3 runs/query majority) | Gate |
|---|---:|---:|---:|
| Passed | 20/25 (80.0%) | **23/25 (92.0%)** | ≥ 90% |
| Precision / recall | 100.0% / 77.3% | **100.0% / 90.9%** | — |
| Should-trigger | 12/15 | **15/15** | — |
| Near-miss | 8/10 | 8/10 | — |
| True-negative (no skill) | 3/3 | 3/3 | — |

- Improvement: **+12.0 pp** (80.0% → 92.0%). A first-run-only post-change pass (23/25) shows
  majority voting is not the cause.
- Remaining failures: `N05` "Update the README." (no skill fired) and `N10` "Migrate the
  database to Postgres." (fired `exploring-idea`; defensibly ambiguous for the imperative form).
- Cost of the real run: 25 × 3 calls, average 5.32 s/call, 1,345,755 tokens total
  (≈17,943/call).

Deterministic mock (CI gate proxy, **not** model evidence): 23/25 = 92.0% on the branch versus
8/25 = 32.0% at baseline. The mock is a keyword heuristic over descriptions, calibrated on this
query set; it exists so CI can catch trigger regressions without credentials.

### 4.3 Behaviour eval — gate not demonstrated (real sample 3/7)

7 fixtures / 48 programmatic assertions (`evals/tasks/`, `scripts/eval_tasks.py`).

| Mode | with-kit | without-kit | Critical failures | Gate (≥ 80%, 0 critical) |
|---|---:|---:|---:|---|
| Deterministic mock (synthetic fixtures) | **7/7** | 0/7 (proves assertions can fail) | **0** | assertion-engine evidence only |
| Real harness, full run (dsh, 1 run/scenario) | **3/7 (42.9%)** | — | **3** | **NOT met** |

Real `dsh` result, full 7 scenarios, 1 run each (`evals/results/behavior-current-dsh.json`;
raw one-pass copy `behavior-current-dsh-run1.json`):

- **PASS (3):** `small-fix`, `vague-ticket`, `review-diff`.
- **FAIL (4):** `normal-feature` (critical `lane-normal` + non-critical `ready-to-build` — the
  behaviour scratch project has no Spec Kit installed, so `specs/`, `plan.md`, `tasks.md` and
  `/speckit-*` cannot exist); `bug` (critical `done-after-evidence` — a fixture ordering bug that
  contradicts `.aiek/core/handoffs.md`, fixed in `03-bug.md` after this raw report);
  `infra` (non-critical `reversible-order` wording only); `parallel` (critical `worker-brief` +
  non-critical `evidence-present` wording).
- Earlier 3-scenario real sample before the fixture-contract fixes:
  `evals/results/behavior-current-dsh-initial.json` = **1/3**.
- Cost of the real run: 7 scenarios × 1 run, 6,243,114 tokens total, 112.37 s/scenario average.
- **No behavioural-safety violation was observed:** the blocked ticket was not coded, and no
  deployment/merge was executed — the failures are missing/ordering evidence text or missing
  Spec Kit setup, plus wording-strict assertions.

The mock path validates the fixture parser, installer wiring, assertion engine and reporting; it
is **not** agent-behaviour evidence. The real failures are dominated by eval-design/fixture gaps
rather than a demonstrated regression of the workflow being evaluated. They are still real: the
plan's behaviour gate (≥ 80% pass, 0 critical failures) is **not met** by this sample, and real
behaviour remains the manual pre-release gate. To close the gap: install Spec Kit in the
behaviour scratch project for Normal/Large scenarios, keep the `03-bug` ordering fix, relax the
wording-strict `infra`/`parallel` assertions where the contract does not mandate exact phrasing,
then re-run all 7 with the real harness and record ≥ 80% with 0 critical. The eval report records
the same gap.

### 4.4 Harness matrix

| Harness | Status on 2026-10-23 | Role / result |
|---|---|---|
| **DeepSeek Harness (`dsh` 0.2.0-rc.2)** | Available, probe `PROBE_OK` | **Primary**; produced the real trigger and behaviour samples above |
| Claude Code (2.1.295) | **Blocked by org policy** (subscription disabled for Claude Code); runner kept | Secondary; no numbers |
| Codex CLI (0.163.0) | Available, `codex exec --json` works; needs isolated `HOME` to hide global `~/.agents/skills` | Optional smoke; no numbers reported |
| `mock` | Always available, no network/secrets | CI quick + nightly gate; never model evidence |

### 4.5 Final verification on the branch

Run on 2026-10-23 from `ai-engineering-kit/`:

| Command | Result |
|---|---|
| `UV_CACHE_DIR=/tmp/aiek-uv-cache bash scripts/check.sh` | **PASS** (15 skills; YAML, references, inventories, wrappers, metadata, size, links, parity) |
| `python3 scripts/check_skills.py . --kit . --require-trigger` | **PASS** (15 skills) |
| `uv run -q --no-project --with pyyaml python scripts/test.py` | **PASS** (16 tests) |
| `python3 scripts/test_scripts.py` | **PASS** (56 tests) |
| `uv run ... python scripts/test-speckit.py` | **PASS** (codex, claude, agy composition) |
| install dry-runs (`full` / `core` / `discovery`) | **PASS**; selected 15 / 11 / 4 skills |
| `python3 scripts/eval_trigger.py --mock` | **PASS** 23/25 (92.0% ≥ 90%) |
| `python3 scripts/eval_tasks.py --mock` | **PASS** 7/7, 0 critical (synthetic) |
| `python3 scripts/eval_tasks.py --harness dsh` (full 7 scenarios) | **3/7 (42.9%), 3 critical — behaviour gate NOT met** (see 4.3) |

The deterministic checks above all pass on the branch. The real behaviour sample does **not**
meet its gate; its failures are traced to eval-design/fixture gaps in 4.3, but the missing
behaviour evidence is recorded here rather than omitted. A real with/without benchmark was not
run (2× behaviour budget); the mock `--both` output is synthetic plumbing only.

---

## 5. What Phase 2 can rely on

| Enabler | Where | Used by Phase 2 for |
|---|---|---|
| `planning.mode` (`speckit\|external\|none`) + `plan_path`/`task_source` | `core/adapter-contract.md`, `core/router.md` | Point Orchexa at its existing docs-based plan without creating a second planner |
| Documentation authority matrix | `core/documentation.md` | Decide which Orchexa doc owns which fact; link, never copy |
| Adapter v2 keys | `core/adapter-contract.md`, `adapters/_template/adapter.md` | Describe repos (BE/FE), fast/full verification, baselines, worktree/branch patterns, adapter refs/scripts |
| `speckit-preset` samples | `adapters/_template/speckit-preset/` | Project-specific constitution/spec/plan/tasks sections that layer on (append to) the kit preset |
| Install profiles | `scripts/install.sh --profile ...` | Install `core` only where discovery skills would duplicate the project's own process |
| Helper scripts | `.aiek/scripts/*.py` | Resolve adapter, run evidence checks, create worktrees, check traceability without hand-written commands |
| Evals + CI | `evals/`, `scripts/eval_*.py`, repo-root `.github/workflows/ai-engineering-kit.yml` | Trigger regressions can be measured now; behaviour fixtures need the §4.3 fixes and a real re-run before that gate is used |

---

## 6. Residual risks and limitations

- **Behaviour eval gate not fully demonstrated (documented limitation).** The full real `dsh`
  run passed 3/7 scenarios (42.9%) with 3 critical assertion failures; mock 7/7 is synthetic
  assertion-engine evidence only. Failures are traced to eval-design gaps: no Spec Kit in the
  `normal-feature` scratch project (so spec/plan/tasks cannot be produced), a DONE-ordering
  fixture bug in `03-bug` (fixed after the raw run), and wording-strict `infra`/`parallel`
  assertions. **No destructive or unsafe action was observed.** The plan's behaviour bar
  (≥ 80%, 0 critical) is not met by the real sample; fixing the fixtures and re-running the full
  real suite is a Phase 2 prerequisite (see §8).
- **Eval coverage is a sample, not a proof.** The trigger set has 25 labeled queries (real
  `dsh`: 23/25) and the behaviour sample 7 scenarios (real `dsh`: 3/7); passing one threshold
  does not guarantee correct skill choice or behaviour on every real request. See the
  limitations sections of the eval reports.
- **Harness variance.** Real-harness evals depend on model behaviour, authentication and quota;
  the primary `dsh` runs and any Claude/Codex smoke runs are recorded separately from the
  deterministic `--mock` results, which are not a substitute for them.
- **Scripts are optional helpers.** They cover the common adapter shapes; unusual projects still
  need manual commands. Safety is by blocklist and dry-run defaults, not a sandbox.
- **Installer profiles change what is installed, not behaviour.** A `core`-only install will
  simply not have discovery skills; the workflow assumes their stage when a request needs it.
- **Docs split did not change the product.** README links to `docs/local-review-ui.md`; the UI
  package is still prepared-but-not-published.
- **Phase 2 unknowns remain Phase 2 work:** Orchexa `AGENTS.md`/`CLAUDE.md` trim, docs
  authority adoption, preset customisation, pilot feature selection (D1, D2, D3, D5, D7).

---

## 7. How to verify this branch

From `ai-engineering-kit/`:

```bash
UV_CACHE_DIR=/tmp/aiek-uv-cache bash scripts/check.sh
python3 scripts/check_skills.py . --kit . --require-trigger
mkdir -p /tmp/aiek-fixture
bash scripts/install.sh /tmp/aiek-fixture --harness codex --dry-run
bash scripts/install.sh /tmp/aiek-fixture --harness codex --profile core --dry-run
bash scripts/install.sh /tmp/aiek-fixture --harness codex --profile discovery --dry-run
uv run -q --no-project --with pyyaml python scripts/test.py      # 16 tests
python3 scripts/test_scripts.py                                   # 56 tests, stdlib only
uv run -q --no-project --with pyyaml python scripts/test-speckit.py  # needs specify on PATH
python3 scripts/eval_trigger.py --mock
python3 scripts/eval_tasks.py --mock
node -e "JSON.parse(require('fs').readFileSync('package.json'))"
```

Expected: `check.sh` and `check_skills.py` pass 15 skills plus inventories; dry-runs pass and
select 15 / 11 / 4 skills for `full` / `core` / `discovery`; tests pass; mock evals pass their
thresholds; `package.json`, `package-lock.json` and `manifest.json` all report 0.2.0. The exact
results recorded on 2026-10-23 are in §4.5. See
[README.md](../README.md#validate-the-kit) for the full validation rationale.

---

## 8. Phase 2 checklist

Phase 2 must not start until the Phase 1 gate is accepted. Hand-off checklist:

- [ ] `scripts/check.sh`, both helper-script test suites, install dry-runs and mock evals pass
      on the merge commit.
- [ ] Real-harness eval numbers are in `docs/eval-2026-10-23.md` and match this handover
      (trigger 23/25 = 92.0%; behaviour 3/7 with 3 critical failures).
- [ ] Behaviour-eval gap closed: install Spec Kit in the behaviour scratch project for the
      Normal scenario, fix the `03-bug` DONE-ordering and the `infra`/`parallel` wording
      assertions, re-run all 7 scenarios on `dsh` (≥ 80%, 0 critical) and update the report.
- [ ] Version 0.2.0 is consistent across `manifest.json`, `package.json` and
      `package-lock.json`; changelog reviewed.
- [ ] `.agents/skills/` canonical / `.claude/` mirror policy accepted (D4).
- [ ] Harness plan accepted: `dsh` primary, Claude/Codex smoke, mock in CI (D6).
- [ ] Phase 2 decisions D1, D2, D3, D5, D7 answered by the tech lead/PO.
- [ ] Orchexa pilot feature chosen and confirmed small, without migration/billing/voice.
- [ ] Docs authority (`core/documentation.md`) mapped onto Orchexa's actual document paths in
      its adapter prose before any spec is written.
- [ ] `--profile core` chosen for Orchexa if its own discovery process already covers those
      stages.
- [ ] Phase 2 owners named for: Spec Kit install/config, preset/templates, adapter cleanup,
      pilot, rollout.

---

## 9. Where to start reading

1. [README.md](../README.md) — what the kit is, install, harnesses.
2. [docs/huong-dan-workflow.md](huong-dan-workflow.md) — Vietnamese walkthrough of all 15 skills.
3. [CHANGELOG.md](../CHANGELOG.md) — grouped Phase 1 changes.
4. [Plan 2 Phase README](plan-2-phases-2026-10-23/README.md) — decisions and Phase 2 scope.
5. [docs/eval-2026-10-23.md](eval-2026-10-23.md) — what was measured and its limits.
