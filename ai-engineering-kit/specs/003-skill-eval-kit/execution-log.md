# Implementation evidence — Skill Eval Kit

Date: 2026-11-08. Scope: MVP implementation and offline verification, plus the usage/CI
integration task. Source of scope/order: [spec](spec.md), [plan](plan.md), [tasks](tasks.md).

## Delivered behavior

Versioned runtime contracts, separate outcome/compliance/safety scoring, per-trial
accounting, shared harness parsers, bounded process groups, fresh committed workspaces,
immutable/redacted evidence, resume, independent bug oracle, human-label replay, paired
pilot suite and JSON/Markdown reports. DSH model patch and macOS read/write canaries are
locally probed; credentials load through the existing DSH bootstrap, not copied into
fixtures or written to evidence. v1 remains an explicitly labeled compatibility path.

Tests first reproduced representative-only usage accounting, partial-answer errors being
hidden, incomplete usage being treated as complete, unknown graders being accepted, missing
baseline commits and bootstrap-loaded credentials escaping raw capture. The corresponding
v2 tests now pass. Old historical report files remain untouched.

## Verification record

[Machine-readable commands, exit codes, test output tails, synthetic pilot accounting and
live preflight](../../evals/results/skill-eval-kit-implementation-2026-11-08.json) are the
acceptance evidence. Detailed local logs live in `.cache/eval-kit-verification/`; immutable
synthetic trial artifacts live in `evals/results/local/pilot-delivery/`, both ignored.

CI quick/nightly jobs now invoke the offline test suite. YAML and job wiring were checked
locally; remote CI has not run. No TypeScript/UI/npm or installer/Spec Kit changes were
made, so those integration/build checks were not rerun. Review here is local self-review,
not an independent reviewer or merge approval. No commit, publish or deploy was performed.

## Live pilot blocker and continuation

The recorded preflight observes DSH `0.2.1-rc.3`, model `deepseek-flash`, verified model
patch and local sandbox capabilities. Authentication for the isolated official-provider
adapter is unavailable through DSH's environment bootstrap. Preflight made zero provider
calls. T013 therefore remains open; no model pass rate or skill-effectiveness claim exists.

Configure the official provider locally using DSH's supported credential configuration,
without putting credentials in this repo or chat. Then follow
[the real-pilot instructions](../../evals/README.md#real-dsh-pilot), rerun preflight, use a
new live experiment directory, and obtain human labels for review/vague-ticket outcomes.
Do not import synthetic labels as real evidence or merge these runs with old v1 reports.

Phase 4 expansion and statistical release gates remain outside this MVP. Semantic LLM
judging remains optional and cannot replace human calibration or deterministic failures.

## 2026-11-09 — managed DSH credentials

User reported DSH ready. Initial preflight still reported missing authentication because
our bridge only loaded environment credentials, while DSH had saved the official key in
its managed credential store. Added read-only resolution through the installed DSH parser:
managed `DEEPSEEK_API_KEY` reference wins over environment fallback; owner-only permissions,
regular-file/size checks and generic error handling reject unsafe/invalid documents.
No credential store is migrated or changed. Only the selected key enters the isolated
child environment; it is scrubbed before transcript capture.

The new test failed before the fix (stored official key was not recognized), then passed.
It also covers managed-store precedence, output scrubbing, unchanged store bytes, unsafe
permissions and malformed-document rejection. Full offline eval suite: 39 tests passed.
Current local preflight: `ready`, DSH `0.2.1-rc.3`, requested model `deepseek-flash`,
no missing capabilities, zero provider calls. Preflight verifies availability, not whether
the key is accepted by the remote provider. The live pilot and human grading are still pending.

Static kit checks, 19 installer tests, 60 helper tests, installer dry-run and both mock
entry points also passed after the fix. Remote CI/npm checks and independent review were
not performed. [Preflight and check evidence](../../evals/results/dsh-managed-credential-preflight-2026-11-09.json).
The user was asked to choose 18 live slots, a two-slot check, or preflight-only because
there is no hard USD cap; no provider call is made while that choice remains pending.

## 2026-11-09 — authorized API-key pilot

User explicitly authorized all 18 slots through DSH/API key, excluding account login.
The effective model patch was checked as provider `deepseek-official`, model `deepseek-flash`.
Initial live execution exposed an environment defect the old canaries missed: DSH's shell
and bundled ripgrep subprocess plumbing created temp artifacts outside the writable root.
Stopped that experiment (8 completed, one interrupted), preserved its artifacts and known
usage, and excluded it from comparative outcomes. No score-based retries or best-run selection.

A regression test reproduced missing trial-local temp paths before the fix. Redirected
TMPDIR/TMP/TEMP and added a required tool_runtime capability probe that invokes the installed
LocalSubprocessRuntime shell and bundled ripgrep without an agent/provider call. 39 eval
tests, static kit/skills checks and diff check passed after the fix. A new frozen experiment
completed 18/18 real slots with no harness errors/timeouts or the original temp failure.

The bug oracle passed all 3/3 trials in each variant. Six semantic outcomes per variant
remain pending actual human labels; CLI exit 3 is expected for this incomplete grading.
No superiority claim. Valid experiment total tokens: no-kit 359870, full-kit 1507120;
trial durations 178.077561s and 417.141163s respectively. Costs remain unavailable; aborted
usage is accounted separately, with one interrupted trial's usage unknown.

[Main report](../../evals/results/pilot-dsh-api-2026-11-09-report.md),
[execution audit](../../evals/results/pilot-dsh-api-2026-11-09-execution.json),
[human-review packet](../../evals/results/pilot-dsh-api-2026-11-09-human-review.md).
T013 stays unchecked until human grading/regrade. No commit/push; remote CI and independent
review were not performed. Source and 18 artifact hashes were verified against the manifest.


## Lite follow-up (user-authorized implementation and PR)

Added a five-skill lite profile in both installers/CLI, with byte-identical Bash/TypeScript
fixture installation and packaged CLI coverage. Small execution is now owned by
`core/small-changes.md`: one pass with fresh targeted checks and self-review, without
mandatory loading of three stage skills. All profiles retain classification and risk gates;
full remains the installation default. Missing prerequisites require escalation, not bypass.

Extended v2 schemas/runner with lite-kit and recorded profile provenance. Added a corrected-
subject exact-content oracle for the Small fixture (including a tampered-body regression),
and a 36-slot no-kit/lite-kit/full-kit suite with the Small case and three original cases.
The login case is risk escalation coverage, not evidence of Small-path savings. Current full
also uses the inline path, so the new suite isolates profile selection under current policy;
compare historical source revisions separately to attribute the router change.

Validation: 43 TypeScript tests, typecheck/lint/build; 41 offline eval tests; 19 installer
and 60 helper tests; static kit/skill checks; lite installer dry-run; npm tarball install and
server smoke; mock trigger 23/25 (existing N05/N10 heuristic mismatches); default mock tasks;
36-slot suite dry-run and mock completed with zero runner errors. Semantic grading remains
pending where applicable. No new model calls; no measured lite quality/time/token claim.
Self-review only; no independent review or browser E2E in this follow-up. PR will be a draft
for review, with the unpublished eval foundation and historical pilot reports included.
