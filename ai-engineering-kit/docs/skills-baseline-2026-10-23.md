# Skills baseline — 2026-10-23

**Purpose:** capture the pre-change triggering/format/behaviour baseline of the AI Engineering
Kit **before** Phase 1 modifies skill descriptions, so post-change numbers in
[eval-2026-10-23.md](eval-2026-10-23.md) are comparable. This document is evidence, not a plan:
[Phase 1 plan](plan-2-phases-2026-10-23/phase-1-kit-optimization.md) §P1.0 T04 and §4.

- **Baseline source:** `main` at commit `85f27c7` ("merge: ai-engineering-kit discovery, PR,
  acceptance and infrastructure skills"), the branch point of `feat/phase-1-kit-optimization`.
- **Branch state when measured:** the working tree contains the Phase 1 skill rewrite, so the
  baseline was measured from an immutable snapshot, never from the working tree:
  `git archive main ai-engineering-kit | tar -x -C /tmp/aiek-baseline` (no checkout, no stash).
- **Harness:** `dsh` (DeepSeek Harness) `0.2.0-rc.2` as the primary real harness; a deterministic
  keyword mock for the offline/CI path. `claude` and `codex` availability was probed and recorded.
- **No fabricated numbers.** Every real-harness number below was produced by the command in
  [Reproduce](#reproduce); mock numbers are explicitly labelled as a heuristic proxy.

---

## 1. Harness matrix at baseline

| Harness | Binary | Status at 2026-10-23 | Evidence |
|---|---|---|---|
| DeepSeek Harness (`dsh`) | `/Users/moment/.local/bin/dsh`, `0.2.0-rc.2` | **Available — primary.** Probe returned `PROBE_OK`; 25 real queries ran. | `dsh headless --json "<prompt>"`; skills read from actual `skill` tool-call events. |
| Claude Code (`claude`) | `/Users/moment/.local/bin/claude`, `2.1.295` | **Unavailable — account restriction.** | `claude -p "Reply with exactly: PROBE_OK" --output-format json` → exit 1, `is_error: true`, result: *"Your organization has disabled Claude subscription access for Claude Code · Use an Anthropic API key instead, or ask your admin to enable access"*. The runner code is kept and marked as a limitation. |
| Codex CLI (`codex`) | `/Users/moment/.local/bin/codex`, `0.163.0` | Available but **not used for baseline**: secondary harness, per D6 decision it would need extra isolation (it also picks up `~/.agents/skills`). | `codex exec --json --skip-git-repo-check "Reply with exactly: PROBE_OK"` → exit 0, `PROBE_OK` in `item.completed`. |
| `mock` | in-repo, deterministic | **Available — used for CI/offline.** | `scripts/eval_trigger.py --mock`; keyword scorer over installed skill descriptions. |

Isolation notes for real dsh runs: the kit was installed with `scripts/install.sh` into a throw-away
scratch project (`.agents/skills`, `.aiek/`, `AGENTS.md`), `DSH_AGENTS_HOME` was pointed at an
empty directory so the machine's global `~/.agents/skills` could not be selected, and scratch
projects were `git init`-ed because dsh resolves the project root by `.git`.

## 2. Static metrics (baseline)

Definitions (also used by `evals/measure_baseline.py`):

- **Use when** — the frontmatter `description` contains the literal phrase "Use when".
- **Negative trigger** — the description contains `not for` / `not used for` / `do not use` /
  `don't use` / `excludes` / `excluded` / `not a substitute` / `instead use`.
- **Trigger examples** — the description contains quoted example phrasings (`'…'` or `"…"`).
- **Body lines** — lines of `SKILL.md` after the YAML frontmatter.

| Skill | Description chars | Use when | Negative trigger | Trigger examples | Body lines | Refs |
|---|---:|:---:|:---:|:---:|---:|---:|
| `accepting-change` | 352 | no | no | no | 95 | 2 |
| `authoring-pr` | 330 | no | yes | no | 79 | 2 |
| `executing-task` | 166 | no | yes | no | 73 | 0 |
| `exploring-idea` | 348 | no | yes | no | 82 | 1 |
| `finishing-branch` | 125 | no | no | no | 38 | 0 |
| `intaking-ticket` | 380 | no | yes | no | 87 | 1 |
| `parallel-development` | 151 | no | no | no | 51 | 1 |
| `reviewing-change` | 142 | no | no | no | 57 | 2 |
| `shaping-feature` | 187 | no | yes | no | 70 | 1 |
| `shaping-project` | 177 | no | no | no | 27 | 1 |
| `shipping-infrastructure` | 381 | no | no | no | 97 | 1 |
| `systematic-debugging` | 285 | no | no | no | 101 | 1 |
| `test-driven-development` | 306 | no | no | no | 84 | 0 |
| `using-worktrees` | 156 | no | no | no | 56 | 0 |
| `verifying-change` | 146 | no | no | no | 62 | 0 |

**Totals:** 15 skills; `Use when` **0/15**; negative trigger **5/15**; quoted trigger examples
**0/15**; description total **3,632 chars** (max 381, min 125); body **1,059 lines / 51,144 chars**
(max 101 lines, all skills ≤ 120); **13** reference files; **0** skill-local script files;
`evals/` **absent** (no trigger set, no behaviour fixtures, no eval harness).

These numbers match the static counts in
[docs/skills-audit-and-plan-2026-10-23.md](skills-audit-and-plan-2026-10-23.md) §1 (1,059 body
lines, 3,632 description chars, 13 reference files, 0 evals), which validates the measurement.

## 3. Trigger eval baseline (25 queries)

Query set: [evals/trigger.json](../evals/trigger.json) — 15 should-trigger + 10 near-miss
(7 near-miss positives with a defensible skill, 3 true negatives; the "open the PR" query accepts
`finishing-branch` or `authoring-pr`). Full rule set is in the JSON `rules` field.

| Mode | Harness | Runs/query | Passed | Accuracy | Precision | Recall | Should-trigger | Near-miss | Negative (no skill) | Avg time/call | Tokens |
|---|---|---|---:|---:|---:|---:|---|---|---|---:|---:|
| Real | `dsh` (tool-call evidence) | 1 | **20/25** | **80.0%** | 100.0% | 77.3% | 12/15 | 8/10 | 3/3 | 6.23 s | 423,696 (≈16,950/query) |
| Mock | keyword scorer | 1 | **8/25** | **32.0%** | 77.8% | 31.8% | 6/15 | 2/10 | 1/3 | <0.01 s | 0 |

**Baseline failures with the real harness (dsh):**

| Query | Prompt | Expected | Observed | Category |
|---|---|---|---|---|
| T01 | "The signup email has a typo — fix it." | executing-task | none | missed (no skill) |
| T06 | "Write the PR description for this branch." | authoring-pr | none | missed (no skill) |
| T12 | "These three tasks are independent; run them in parallel." | parallel-development | none | missed (no skill) |
| N05 | "Update the README." | executing-task | none | missed (no skill) |
| N10 | "Migrate the database to Postgres." | executing-task | shipping-infrastructure | wrong skill |

No should-trigger query picked a *wrong* skill under dsh: the baseline failure mode is
**under-triggering** (12/15 should-trigger queries fired a skill; the 3 misses are queries whose
description vocabulary did not clearly claim the request), plus one near-miss miss. Precision on
the 20 positives is 100% (no false positives on the 3 true-negative queries).

**Why the mock baseline is so much lower (32% vs 80%) and why it is not a model result:** the mock
is a deterministic keyword scorer over the *installed skill descriptions*; it rewards trigger
vocabulary (`Use when …`, quoted example phrasings) and negative vocabulary (`Not for …`), both of
which the baseline descriptions almost entirely lack (see §2). It is reported to calibrate the CI
proxy, not as a model baseline. The real-harness 80% is the baseline number to compare against.

**Sample cost/time:** the real baseline run was 25 calls × 1 run: 423,696 tokens total
(≈16,950/query, summed from dsh per-step usage events) and 6.23 s per call average wall time
(excluding scratch install, which took 0.36 s). The Phase 1 plan's T04 asks for token/time on
"5 sample tasks"; the 25-call aggregate above is a superset with the same per-call cost shape and is
what is recorded here (per-query token split is not emitted by the harness event stream).

## 4. Behaviour eval baseline

The behaviour harness and the 7 fixtures ([evals/tasks/](../evals/tasks/)) were created in this
task, but a real-harness behaviour baseline was **not measured**: each behaviour run is a full task
execution (minutes, larger token budget), and the plan's §4.2 baseline is about the current state
of triggering plus the fixture rubric, not a numeric pre-change pass rate. The synthetic `--mock`
run returns the fixtures' gold responses and therefore validates the assertion engine only.

Behaviour evidence available at baseline:
- Fixture framework: 7 scenarios, 48 concrete assertions (lane, artifacts, evidence table,
  BLOCKED + questions, `file:line` + severity, decision/rollback, parallel decision + worker brief
  + combined verification), `scripts/eval_tasks.py --mock` = 7/7 synthetic.
- The `mock` response for each scenario is in the fixture; it is **not** an agent result.

Post-change behaviour numbers are in [eval-2026-10-23.md](eval-2026-10-23.md) §3.

## 5. Limitations

1. **Real baseline is 1 run/query, not 3-run majority.** The plan's T25 wants 3 runs/query; 25×3
   real calls for baseline + 25×3 for post-change was judged too costly/time-heavy for this
   iteration. Majority-of-3 is implemented (`--runs 3`) and was run for the post-change kit; the
   baseline is a documented 1-run sample.
2. **Mock numbers are not model numbers.** The mock is deterministic and phrase-sensitive; the
   baseline descriptions have no `Use when`/negative trigger phrases, so the mock floor is
   artificially low. Do not quote mock 32% as "the model triggered 32%".
3. **Trigger prompt is a bounded probe, not task execution.** The prompt suffix says "do not
   implement or edit files" and asks for a first-line `SKILL_USED`; dsh skill use is read from
   actual `skill` tool-call events, so the measurement is selection behaviour, not task quality.
4. **Claude Code is unavailable in this environment** (exact error above); Codex is available but
   not used for baseline. Harness-agnostic runners for both exist (`--harness claude|codex`).
5. **Token counts are approximate**: summed from per-step `usage` events; wall time is per-call
   only. macOS has no `timeout(1)`, so timeouts are Python `subprocess` timeouts.
6. **Behaviour baseline with a real harness is not measured** (see §4); only the framework and the
   synthetic plumbing run exist.
7. **The snapshot is a source archive**, not a git checkout: `evals/` and the eval scripts do not
   exist inside the baseline kit, so the eval scripts were run from the working branch with
   `--kit-root /tmp/aiek-baseline/ai-engineering-kit` (they install that snapshot, they do not read
   the working tree's skills).

## 6. Reproduce

```bash
cd ai-engineering-kit

# 1. Immutable baseline snapshot (no branch change, no stash)
rm -rf /tmp/aiek-baseline && mkdir -p /tmp/aiek-baseline
git archive main ai-engineering-kit | tar -x -C /tmp/aiek-baseline

# 2. Static metrics (baseline; JSON or markdown)
python3 evals/measure_baseline.py --kit-root /tmp/aiek-baseline/ai-engineering-kit --format markdown

# 3. Trigger eval - offline heuristic floor
python3 scripts/eval_trigger.py --mock \
  --kit-root /tmp/aiek-baseline/ai-engineering-kit \
  --queries "$PWD/evals/trigger.json" \
  --kit-label baseline-main-85f27c7 \
  --out evals/results/trigger-baseline-mock.json

# 4. Trigger eval - real DeepSeek Harness (primary; ~2-4 min, ~425k tokens)
python3 scripts/eval_trigger.py --harness dsh --runs 1 \
  --kit-root /tmp/aiek-baseline/ai-engineering-kit \
  --queries "$PWD/evals/trigger.json" \
  --kit-label baseline-main-85f27c7 \
  --out evals/results/trigger-baseline-dsh.json

# 5. Kit checks on the baseline snapshot (needs PyYAML or uv)
UV_CACHE_DIR=/tmp/aiek-uv-cache bash /tmp/aiek-baseline/ai-engineering-kit/scripts/check.sh
```

Machine-readable baselines: [evals/results/trigger-baseline-dsh.json](../evals/results/trigger-baseline-dsh.json)
and [evals/results/trigger-baseline-mock.json](../evals/results/trigger-baseline-mock.json)
(plus the post-change counterparts in [eval-2026-10-23.md](eval-2026-10-23.md)).
