# Evals — AI Engineering Kit

Two eval suites, both harness-agnostic and CI-safe in deterministic `--mock` mode:

| Artifact | What it is | Runner |
|---|---|---|
| [`trigger.json`](trigger.json) | 25 trigger queries: 15 should-trigger + 10 near-miss (7 near-miss positives, 3 true negatives; "open the PR" accepts `finishing-branch` or `authoring-pr`) | [`../scripts/eval_trigger.py`](../scripts/eval_trigger.py) |
| [`tasks/*.md`](tasks/) | 7 behaviour fixtures (Small fix, Normal feature, bug, vague ticket, review diff, infra, parallel), each with a scratch-project setup, concrete programmatic assertions, a synthetic mock response and a naive without-kit response | [`../scripts/eval_tasks.py`](../scripts/eval_tasks.py) |
| [`measure_baseline.py`](measure_baseline.py) | Static metrics (description length, `Use when` / negative triggers / quoted examples, body size, references) for a baseline snapshot vs the current tree | `python3 evals/measure_baseline.py --kit-root <kit>` |
| [`results/`](results/) | Machine-readable reports from the runs quoted in [docs/eval-2026-10-23.md](../docs/eval-2026-10-23.md) and [docs/skills-baseline-2026-10-23.md](../docs/skills-baseline-2026-10-23.md) | written by `--out` |

## Run it

```bash
cd ai-engineering-kit

# Offline / CI (deterministic, no model, no network)
python3 scripts/eval_trigger.py --mock --runs 1
python3 scripts/eval_tasks.py --mock

# Real harness: dsh is primary; auto probes dsh > claude > codex
python3 scripts/eval_trigger.py --harness dsh --runs 3
python3 scripts/eval_tasks.py --harness dsh --scenario small-fix --scenario vague-ticket

# Baseline snapshot from main (no branch change)
rm -rf /tmp/aiek-baseline && mkdir -p /tmp/aiek-baseline
git archive main ai-engineering-kit | tar -x -C /tmp/aiek-baseline
python3 scripts/eval_trigger.py --mock \
  --kit-root /tmp/aiek-baseline/ai-engineering-kit \
  --queries "$PWD/evals/trigger.json" --kit-label baseline-main
```

Trigger exit code is non-zero below 90% accuracy; behaviour is non-zero below 80% pass rate **or**
on any critical assertion failure (claiming DONE without evidence, coding a BLOCKED ticket,
deploying without approval). `--json` / `--out PATH` emit machine-readable reports.

## How the harnesses are used

- **`dsh` (DeepSeek Harness) is the primary real harness.** Skill use is read from actual `skill`
  tool-call events in `dsh headless --json`, not from the self-reported `SKILL_USED:` line.
- **`claude` / `codex`** are optional smoke harnesses; they expose no reliable skill tool-call
  event, so they fall back to the declared `SKILL_USED:` line and are marked
  `"source": "declared"`. `auto` probes `dsh > claude > codex` and **never fabricates a pass**: if no
  harness works it falls back to `--mock` and records the exact failure in `limitations`.
- **`mock`** is a deterministic keyword scorer (trigger) / synthetic fixture responder (behaviour)
  for CI and offline baselines. It is labelled `synthetic: true` in every report and is **not**
  evidence of model behaviour; it validates description coverage, fixture parsing, installer wiring
  and the assertion engine.

Real runs happen in a throw-away scratch project: the kit is installed by the same
`scripts/install.sh` users run, the project is `git init`-ed (dsh finds the project root by `.git`),
and `DSH_AGENTS_HOME` is isolated so global user skills cannot pollute the measurement. Every
harness call is bounded by a Python subprocess timeout (macOS has no `timeout(1)`).

## Assertion contract notes

Two behaviour checks are deliberately ordering/wording-neutral because the kit contract is:

- **DONE handoff format** (`.aiek/core/handoffs.md`): the report *starts* with the status word
  (`DONE: ...`) on the first line, then Summary/Files/Checks with the evidence table. Assertions
  therefore check that `DONE` and an evidence table exist (and that the evidence is fresh), not that
  evidence text appears before `DONE`. `small-fix` keeps `done-present` (non-critical) plus the
  `evidence-table` check; no critical assertion depends on ordering.
- **BLOCKED handoff** (plan §4.2): the requirement is "BLOCKED + câu hỏi" — a blocked handoff that
  asks a concrete question, not a count of `?` characters. `vague-ticket` marks
  `asks-questions` (min 1) critical and tracks the richer ideal, `multiple-questions` (min 2), as a
  non-critical assertion. The substantive critical assertions (`blocked-handoff`, `no-code-change`,
  `no-spec-created`, `no-fabricated-done`) stay critical.

## Adding queries or scenarios

- Trigger query: add an object to `trigger.json` with `id`, `kind`, `prompt`, `expected_skills`
  (empty list = must not trigger anything), `preferred_skills` (for the wrong-skill matrix) and
  `reason`. Keep a defensible acceptable set for ambiguous prompts.
- Behaviour scenario: add a new Markdown file to `tasks/`; use the section layout of the existing
  fixtures (`## Prompt`, `## Setup` with `### relative/path` blocks, `## Assertions` as a JSON
  array, optional `## Mock changes`, `## Mock response`, `## Mock response without kit`). Prefer
  concrete assertions (files, `file:line`, evidence tables, BLOCKED + questions) over prose checks.
