# parallel

- id: parallel
- title: Parallel — two independent tasks
- critical: true
- timeout_s: 900
- lane: NORMAL

## Prompt
```text
Two independent tasks: (a) add a /healthcheck endpoint that returns 200, and (b) update the README with setup instructions. Run them in parallel if appropriate.
```

## Setup
### app/main.py
```text
def create_app():
    routes = {}

    def route(path):
        def register(handler):
            routes[path] = handler
            return handler

        return register

    @route("/")
    def index():
        return (200, "ok")

    return routes
```
### README.md
```text
# Demo service
```
### tests/test_main.py
```text
import unittest

from app.main import create_app


class MainTest(unittest.TestCase):
    def test_index(self):
        self.assertIn("/", create_app())


if __name__ == "__main__":
    unittest.main()
```

## Assertions
```json
[
  {
    "id": "parallel-decision",
    "kind": "output_regex",
    "pattern": "(?i)(parallel|concurren)",
    "description": "Makes an explicit parallel-vs-sequential decision with a reason",
    "critical": true
  },
  {
    "id": "worker-brief",
    "kind": "output_regex",
    "pattern": "(?i)(worker (brief|[12ab])|brief for|agent [12ab]|workers?.{0,160}(disjoint|concurr|assigned|scope)|disjoint files)",
    "description": "Concrete per-worker assignment/brief evidence (named or file-scoped units), not only the literal phrase 'worker brief'",
    "critical": true
  },
  {
    "id": "combined-verification",
    "kind": "output_regex",
    "pattern": "(?i)(combined verification|verify (both|the combined)|run both|final verification|one combined)",
    "description": "Runs one combined verification after integrating both results",
    "critical": true
  },
  {
    "id": "healthcheck-implemented",
    "kind": "file_contains",
    "path": "app/main.py",
    "pattern": "healthcheck",
    "description": "The healthcheck endpoint exists",
    "critical": true
  },
  {
    "id": "readme-updated",
    "kind": "file_contains",
    "path": "README.md",
    "pattern": "(?i)setup|install|run",
    "description": "The README setup section is written",
    "critical": true
  },
  {
    "id": "evidence-present",
    "kind": "output_regex",
    "pattern": "(?i)(evidence|verification|combined gate|checks? ?[(]?(after|run))",
    "description": "Combined verification evidence, including a 'Checks (...)'' table",
    "critical": false
  }
]
```

## Mock changes
### app/main.py
```text
def create_app():
    routes = {}

    def route(path):
        def register(handler):
            routes[path] = handler
            return handler

        return register

    @route("/")
    def index():
        return (200, "ok")

    @route("/healthcheck")
    def healthcheck():
        return (200, "healthy")

    return routes
```
### README.md
```text
# Demo service

## Setup

Run `python3 -m unittest` from the repository root.
```

## Mock response
```text
Lane: NORMAL (two independent Small units, combined into one change).

Parallel decision: yes, safe to run concurrently — (a) `app/main.py` and (b) `README.md` touch disjoint files, neither depends on the other, no shared migration or generated file. Isolation: worker A in its own worktree, worker B in its own worktree.

Worker brief A: add `/healthcheck` returning `(200, "healthy")` in `app/main.py`; run `python3 -m unittest`; report diff + exit code.
Worker brief B: add a "## Setup" section to `README.md`; no code changes; report diff.

Both workers finished; results merged by hand in the main tree.
Combined verification: `python3 -m unittest tests.test_main` exit 0 after the merge; the healthcheck route is present and the README setup section renders.

Evidence:
| Check | Command | Exit code |
| --- | --- | --- |
| combined suite | python3 -m unittest | 0 |
| healthcheck route | python3 -c "from app.main import create_app; print('/healthcheck' in create_app())" | 0 |

DONE — both independent tasks integrated and verified once, together.
```

## Mock response without kit
```text
I added the healthcheck and updated the README. Both changes are in.
```
