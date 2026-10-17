---
name: reviewing-change
description: "Reviews implemented, verified changes before completion or integration, and evaluates incoming review feedback. Does not replace verification."
---

# Reviewing a Change

Catch problems before a human spends review time on them, and handle incoming feedback on
its technical merits.

## Who reviews

Use the reviewer policy in `.aiek/core/WORKFLOW.md`, including adapter-required human review
and the fallback when independent review is unavailable.

## Requesting a review

1. Record `BASE`, `HEAD`, task-owned paths, and initial working-tree status. Include staged,
   unstaged and untracked task changes; exclude unrelated pre-existing work.
2. Give the reviewer: what was built (2–3 lines), the requirements (spec.md acceptance
   criteria and the relevant plan sections, or the Small request), the git range, the
   adapter's conventions, and the verification evidence.
3. Never give it your session history. It judges the diff against the requirements.

## Review checklist

- **Requirements:** every acceptance criterion / task met? anything extra (scope creep)?
  anything misunderstood? A spec's silence is not permission: judge unspecified behavior
  by what a reasonable user would expect.
- **Correctness:** edge cases, error handling, concurrency, data integrity.
- **Security:** input validation, authz checks, secrets, injection, the adapter's `risk_areas`.
- **Tests:** do they test real behavior? would they fail if the code broke?
- **Design:** fits the plan and existing patterns; no needless abstraction or duplication.
- **Operability:** migrations reversible, logging, config, backwards compatibility.

## Severity

| Level | Meaning | Action |
|---|---|---|
| Critical | bug, security hole, data loss, broken feature | fix before DONE |
| Important | missing requirement, poor error handling, test gap, design problem | fix before DONE, or NEEDS DECISION if fixing changes scope |
| Minor | style, naming, small optimizations, docs | fix if trivial, else list under deferred in DONE |

Each finding states: `file:line`, what is wrong, why it matters, suggested fix.

## Fix loop

Fix Critical/Important findings in one pass, re-run `verifying-change`, then ask the same
reviewer to confirm each finding is ADDRESSED or NOT ADDRESSED (scoped re-review, not a new
full review). After two rounds with open Critical/Important findings, report BLOCKED or
NEEDS DECISION instead of looping.

## Receiving feedback

See `references/receiving-feedback.md`. In short: verify each point against the code before
acting, push back with evidence when it is wrong for this codebase, clarify unclear
items while continuing independent, understood fixes. Check each affected behavior.
No performative agreement.

_Adapted from `requesting-code-review` and `receiving-code-review` of obra/superpowers (MIT, © 2025 Jesse Vincent).
License in the kit's `NOTICE.md`._
