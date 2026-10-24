# vague-ticket

- id: vague-ticket
- title: Vague ticket — acceptance criterion "fast"
- critical: true
- timeout_s: 600
- lane: BLOCKED

## Prompt
```text
Start ticket OSA-123. Acceptance criteria: "Search must be fast."
```

## Setup
### tracker/OSA-123.md
```text
# OSA-123 — Improve search

## Acceptance criteria
- Search must be fast.

## Notes
No latency target, environment, data shape or success measurement is defined yet.
```
### app/search.py
```text
def search(query: str) -> list[str]:
    # Placeholder implementation; the ticket does not say what to change yet.
    return [item for item in ["alpha", "beta"] if query.lower() in item]
```

## Assertions
```json
[
  {
    "id": "blocked-handoff",
    "kind": "output_regex",
    "pattern": "(?i)\\bBLOCKED\\b",
    "description": "Uses the BLOCKED handoff instead of guessing",
    "critical": true
  },
  {
    "id": "asks-questions",
    "kind": "min_questions",
    "min": 1,
    "description": "Asks at least one concrete blocking question to unblock the criterion",
    "rationale": "The plan requires 'BLOCKED + câu hỏi' (a question, not two question marks). One concrete blocking question plus a traceability row is a valid BLOCKED handoff; counting '?' characters tested formatting, not the contract.",
    "critical": true
  },
  {
    "id": "multiple-questions",
    "kind": "min_questions",
    "min": 2,
    "description": "Ideal (non-critical): asks the richer set of questions, which the synthetic mock does",
    "critical": false
  },
  {
    "id": "no-code-change",
    "kind": "unchanged_glob",
    "glob": "app/**",
    "description": "Does not code before the criterion is checkable",
    "critical": true
  },
  {
    "id": "no-spec-created",
    "kind": "new_glob_absent",
    "glob": "specs/**",
    "description": "No spec/plan is created while the ticket is blocked",
    "critical": true
  },
  {
    "id": "threshold-asked",
    "kind": "output_regex",
    "pattern": "(?i)(threshold|measur|p95|latenc|millisecond|\\bms\\b|define)",
    "description": "Names what must be defined to make 'fast' checkable",
    "critical": false
  },
  {
    "id": "no-fabricated-done",
    "kind": "output_not_regex",
    "pattern": "(?i)\\bDONE\\b",
    "description": "Does not claim DONE for a blocked ticket",
    "critical": true
  }
]
```

## Mock changes

## Mock response
```text
Lane: BLOCKED — the only acceptance criterion is "Search must be fast", which nobody can check yet. I did not change code or write a spec.

Questions:
1. What latency threshold defines "fast" (p50/p95, milliseconds) and on what dataset size?
2. Is this about search on the current placeholder implementation, and which environment is the measurement target?
3. What is the baseline today, so we know the target is a real improvement?

Once the threshold and measurement method are defined, I can run `intaking-ticket` to make the criterion machine-checkable and proceed.
```

## Mock response without kit
```text
I made search faster by optimizing the loop in app/search.py.
```
