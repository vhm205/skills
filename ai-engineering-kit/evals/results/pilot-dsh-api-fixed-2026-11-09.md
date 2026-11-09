# Eval report

Synthetic: False. Verdict: inconclusive.

Quality = successes / graded completed trials; end-to-end = successes / all started trials.
Coverage = graded completed / all started. Errors stay in end-to-end denominator.

| Variant | Success/graded | Quality | End-to-end | Coverage | Errors | Critical | Tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full-kit | 3/3 | 100.0% | 33.3% | 33.3% | 0 | 0 | 1507120 |
| no-kit | 3/3 | 100.0% | 33.3% | 33.3% | 0 | 0 | 359870 |

## Per scenario

- bug: outcome delta 0.0 (full-kit minus no-kit).
- review-diff: outcome delta None (full-kit minus no-kit).
- vague-ticket: outcome delta None (full-kit minus no-kit).

## Limits

- Small pilot; no statistical superiority claim.
- Cost unavailable without a versioned price table and complete usage.
- Unknown observations are not failures or proof of absence.
- macOS sandbox capability probes are local; Linux requires an isolated runner adapter.
- DSH official provider only; no custom global plugins or settings are loaded.
- Model patch pins requested identity; provider-returned model identity may be unavailable.
