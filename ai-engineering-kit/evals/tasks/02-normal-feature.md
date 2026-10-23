# normal-feature

- id: normal-feature
- title: Normal feature — CSV export for reports
- critical: true
- timeout_s: 900
- lane: NORMAL

## Prompt
```text
Add CSV export to reports.
```

## Setup
### reports/summary.py
```text
from typing import Any

ROWS = [
    {"name": "alpha", "total": 10},
    {"name": "beta", "total": 20},
]


def report_rows() -> list[dict[str, Any]]:
    return list(ROWS)
```
### tests/test_summary.py
```text
import unittest

from reports.summary import report_rows


class SummaryTest(unittest.TestCase):
    def test_rows(self):
        self.assertEqual(len(report_rows()), 2)


if __name__ == "__main__":
    unittest.main()
```
### README.md
```text
# Demo reports app

`python3 -m pytest` or `python3 -m unittest` runs the tests.
```

## Assertions
```json
[
  {
    "id": "lane-normal",
    "kind": "output_regex",
    "pattern": "(?i)(lane.{0,80}normal|normal.{0,80}lane)",
    "description": "States the NORMAL lane (either word order; the kit does not mandate a literal 'Lane:' prefix)",
    "critical": true
  },
  {
    "id": "planning-artifact",
    "kind": "output_regex",
    "pattern": "(?is)(spec\\.md|specs/|plan\\.md|tasks\\.md|external plan|planning artifact)",
    "description": "Uses the planning artifact path instead of an ad-hoc plan",
    "critical": true
  },
  {
    "id": "ready-to-build",
    "kind": "output_regex",
    "pattern": "(?i)(ready to build|ready to implement|specs/|plan[.]md|tasks[.]md)",
    "description": "Non-critical readability signal that planning happened (readiness itself is proven by the critical spec-artifact-created assertion)",
    "critical": false
  },
  {
    "id": "spec-artifact-created",
    "kind": "glob_exists",
    "glob": "specs/**",
    "description": "A spec/plan/tasks artifact exists for the Normal lane",
    "critical": true
  },
  {
    "id": "feature-implemented",
    "kind": "changed_glob",
    "glob": "reports/**",
    "description": "Reports code was changed to implement the feature",
    "critical": true
  },
  {
    "id": "evidence-present",
    "kind": "output_regex",
    "pattern": "(?i)(evidence|verification)",
    "description": "Verification evidence is reported",
    "critical": true
  },
  {
    "id": "self-review",
    "kind": "output_regex",
    "pattern": "(?i)(review|self-review)",
    "description": "Review/self-review step is not skipped",
    "critical": false
  },
  {
    "id": "done-after-evidence",
    "kind": "output_order",
    "before": "(?i)(evidence|verification)",
    "after": "(?i)\\bDONE\\b",
    "description": "DONE is claimed only after evidence is reported",
    "critical": true
  }
]
```

## Mock changes
### reports/export.py
```text
import csv
import io

from reports.summary import report_rows


def to_csv() -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["name", "total"])
    writer.writeheader()
    writer.writerows(report_rows())
    return buffer.getvalue()
```
### specs/001-csv-export/spec.md
```text
# CSV export for reports

## Requirements
- FR-1: export report rows as CSV with a header row.
- FR-2: return the CSV as a string so callers can stream or save it.

## Acceptance
- AC-1: exporting the two fixture rows yields a header plus two data rows.
```
### specs/001-csv-export/plan.md
```text
# Plan — CSV export

1. Add `reports/export.py::to_csv`.
2. Add a unit test for header and row count.
3. Run the test suite as the verification gate.
```
### specs/001-csv-export/tasks.md
```text
# Tasks — CSV export

- [x] T001 Add `to_csv` in `reports/export.py`
- [x] T002 Cover it with a unit test
- [x] T003 Run the suite and collect evidence
```

## Mock response
```text
Lane: NORMAL (new user-visible behaviour spanning spec, plan, implementation and tests).

Plan: `specs/001-csv-export/` now holds `spec.md`, `plan.md` and `tasks.md`. Spec Kit owns this plan; no second plan was written.
READY TO BUILD — implemented T001–T003.

Evidence:
| Check | Command | Exit code |
| --- | --- | --- |
| suite | python3 -m unittest | 0 |
| csv rows | python3 -c "from reports.export import to_csv; print(len(to_csv().splitlines()))" | 0 |

Self-review: export escapes values through the `csv` module and adds no dependency. Verification passed before the claim.

DONE — CSV export implemented for reports with spec/plan/tasks, tests green.
```

## Mock response without kit
```text
I added a to_csv function in reports/export.py and it should work now.
```
