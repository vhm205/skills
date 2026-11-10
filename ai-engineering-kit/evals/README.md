# Evals — AI Engineering Kit

Eval v2 separates **task outcome**, **kit compliance**, and **efficiency**. A baseline can
complete the task without naming a lane or printing the kit's evidence table. A polished
report cannot override a failing independent test. No composite badge or superiority claim
is produced by this pilot.

## Quick start (offline)

```bash
python3 scripts/test_evals.py
python3 scripts/eval_trigger.py --mock --runs 1
python3 scripts/eval_tasks.py --mock --both --out /tmp/aiek-behavior-v2.json
python3 scripts/eval_tasks.py --suite evals/suites/pilot.json --mock \
  --experiment-dir evals/results/local/pilot-offline --out /tmp/aiek-pilot-offline.json
```

The pilot schedules 3 scenarios × 3 repeats × 2 variants = 18 records. Mock repeats remain
separate to test scheduling and accounting; they are deterministic synthetic inputs, not
independent model trials. Mock success means plumbing completed. Human outcomes remain
pending-review, legacy fixtures without an independent grader remain unavailable.

The public behavior CLI now defaults to report v2. Add `--report-version 1` to obtain the
explicitly labeled legacy report; it retains legacy scoring and must not be compared to
v2 outcome rates. Historical files under results/ are preserved as originally recorded.
The trigger CLI remains the existing trigger suite and uses shared harness adapters.

## Real DSH pilot

Run local probes first. No provider request is made by preflight:

```bash
python3 scripts/eval_tasks.py --suite evals/suites/pilot.json \
  --model deepseek-flash --preflight --out /tmp/aiek-dsh-preflight.json
python3 scripts/eval_tasks.py --suite evals/suites/pilot.json \
  --model deepseek-flash --experiment-dir evals/results/local/pilot-dsh \
  --out /tmp/aiek-pilot-dsh.json
```

Choose the explicit model available to your provider. The bundled suite leaves model null
so execution cannot silently use a changing default. Current isolated DSH adapter targets
the official DeepSeek provider on macOS: it verifies the launcher model patch and OS sandbox
canaries, probes the installed DSH shell/ripgrep subprocess runtime without a model call,
then starts each trial in a fresh DSH home, with only installed workspace skills.
Authentication reads the managed `DEEPSEEK_API_KEY` reference from DSH's owner-only
credential store using DSH's installed parser, then falls back to DSH's environment bootstrap.
The managed store wins, matching DSH precedence. The bridge reads without migration or
mutation and rejects invalid or broadly readable stores. Credentials stay in child memory,
are neither copied to workspaces nor written to reports. No custom global plugins/settings are loaded.
Only the provider credential and supported proxy variables pass to the isolated child.
`TMPDIR`/`TMP`/`TEMP` point inside each trial root so tool subprocess artifacts remain writable.

Agent writes stay inside its temporary root; it cannot read this source checkout or global
skill/config roots. Private grader runs use a clean replica with original tests, bounded
processes and a separate network-disabled sandbox on macOS. On platforms without that
boundary, offline trusted-fixture tests still run, but live preflight reports unsupported.
This is not a certification against arbitrary malicious or eval-aware submitted programs.

Limits: 18 primary slots, 900 seconds per trial, bounded output, no automatic retries. The
suite does not enforce a hard dollar/token cap when provider telemetry is unavailable.
Auth/install errors stop remaining slots as planned; fix the external condition, then resume
with exactly the same command plus `--resume`. A changed suite/source/grader manifest needs
a new experiment directory. Interrupted started slots are recorded, never automatically
retried. Probe/auth failures are not transformed into successful trials.

Claude/Codex parsing remains available, but isolated live v2 support is disabled until their
model/config/process capabilities are verified. agy/omp are not supported by this MVP.

## Evidence and replay

Each experiment contains immutable manifest/source hashes, randomized paired schedule,
per-trial started/completed records, bounded redacted transcripts/events, before/after
snapshots, patches, grader evidence and versioned reports. `evals/results/local/` is ignored.
Raw environment/configuration dumps are never persisted. Review exported artifacts before
sharing; redaction handles known credentials and common token formats, not all possible
sensitive prose. User-selected summary outputs must be outside the immutable experiment root.

Two pilot outcomes need human labels. Fill the generated reviews/request-*.json using the
[rubrics](labels/README.md), preserving artifact hashes and omitting variant knowledge:

```bash
python3 scripts/eval_tasks.py --regrade evals/results/local/pilot-dsh \
  --labels /tmp/human-labels.json --out /tmp/aiek-pilot-graded.json
```

No agent is called by regrading; original trials are untouched. A new report references the
label hash. The bug oracle checks normalization and lookup behavior, original baseline tests
and preservation. Review and vague-ticket outcomes require semantic labels; keyword checks
are retained only as compliance diagnostics and are labeled self-report or filesystem.

## Reading the numbers

- Quality rate = successful outcomes / graded completed trials.
- End-to-end rate = successful outcomes / all started trials, including errors.
- Coverage = graded completed / all started; inspect this before interpreting quality.
- Required outcome failures fail the task; optional checks remain diagnostics.
- Missing usage is null, with known-token subtotal and coverage. Every trial counts;
  majority voting does not replace per-trial results. Duration includes trial overhead.
- Cost and human intervention counts remain unavailable without reliable telemetry/labels.
- Synthetic, manual and real evidence must not be merged. Small samples and partial human
  labels yield inconclusive, never a claim that the kit is better by default.

Exit codes: 0 = offline plumbing/planning/regrade completed (or a complete real quality gate
met); 1 = scored failure/critical violation; 2 = configuration, capability, execution or
grader error; 3 = real outcomes need review or have incomplete coverage. Exit 0 is not a
release certification. Every current report has release_proof=false and verdict=inconclusive.

Implementation scope/acceptance belongs to [the feature spec](../specs/003-skill-eval-kit/spec.md);
this guide owns usage. No new eval command or dependencies are installed into consumer projects.

## Legacy suite reference

The following section documents v1 fixtures and historical measurements. Its behavior
commands require `--report-version 1`; historical pass counts do not measure v2 outcome.



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

## Lite comparison

`evals/suites/pilot-lite.json` schedules 36 trials: a Small copy fix plus the original three tasks, three repeats,
and `no-kit`, `lite-kit`, `full-kit`. Each kit variant installs its actual profile into a
fresh workspace; reports record the selected profile and installed skills. The full-kit
variant uses the current router, including its Small inline path. This compares installation
profiles under the new policy, not old-full versus new-lite; historical pilot results have
a different source digest and must not be pooled with this suite.

```bash
python3 scripts/eval_tasks.py --suite evals/suites/pilot-lite.json --dry-run
python3 scripts/eval_tasks.py --suite evals/suites/pilot-lite.json --mock
```

Mock checks plumbing only. For a live run, explicitly select the API model, a new experiment
directory and an output path as in the pilot instructions. No live lite result exists yet.
The original bug case changes login behavior (a classification hard trigger), so it is an
escalation check, not a Small-path efficiency benchmark. Vague intake tests missing-prerequisite
behavior in lite; retain independent semantic grading instead of requiring identical prose.
Add representative low-risk Small cases and harder holdout tasks before deciding defaults.
Evaluate outcome and critical violations first, then time/tokens; compliance alone is not quality.
