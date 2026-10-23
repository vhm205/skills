# bug

- id: bug
- title: Bug — login 500 when the email contains a plus sign
- critical: true
- timeout_s: 900
- lane: NORMAL

## Prompt
```text
Login fails with a 500 when the email has a plus sign. Find the cause and fix it.
```

## Setup
### app/auth.py
```text
USERS = {
    "alice@example.com": {"id": 1, "name": "Alice"},
    "bob@example.com": {"id": 2, "name": "Bob"},
}


def normalize_email(email: str) -> str:
    # Deliberately buggy: splits on "+" to drop sub-addressing, but then keeps the
    # wrong half, so lookups for plus-addressed mail never match.
    local, _, domain = email.partition("@")
    local = local.split("+")[1] if "+" in local else local
    return f"{local}@{domain}"


def find_user(email: str) -> dict:
    return USERS[normalize_email(email)]
```
### tests/test_auth.py
```text
import unittest

from app.auth import find_user


class AuthTest(unittest.TestCase):
    def test_plain_email(self):
        self.assertEqual(find_user("alice@example.com")["id"], 1)


if __name__ == "__main__":
    unittest.main()
```
### README.md
```text
# Demo auth app

Run tests with `python3 -m unittest`.
```

## Assertions
```json
[
  {
    "id": "root-cause",
    "kind": "output_regex",
    "pattern": "(?i)(root cause|root-cause|hypothesis|the cause)",
    "description": "States a root-cause hypothesis instead of patching symptoms",
    "critical": true
  },
  {
    "id": "regression-test",
    "kind": "output_regex",
    "pattern": "(?i)(regression test|failing test|reproduc)",
    "description": "Registers a reproducing/regression test",
    "critical": true
  },
  {
    "id": "fix-at-source",
    "kind": "changed_glob",
    "glob": "app/auth.py",
    "description": "The bug is fixed at the source in app/auth.py",
    "critical": true
  },
  {
    "id": "test-updated",
    "kind": "changed_glob",
    "glob": "tests/**",
    "description": "A test was added or updated for the regression",
    "critical": false
  },
  {
    "id": "plus-sign-handled",
    "kind": "file_not_contains",
    "path": "app/auth.py",
    "pattern": "local.split(\"+\")[1]",
    "description": "The buggy plus-splitting line no longer exists",
    "critical": true
  },
  {
    "id": "evidence-present",
    "kind": "output_regex",
    "pattern": "(?i)(evidence|verification)",
    "description": "Reports evidence for the fix",
    "critical": true
  },
  {
    "id": "done-present",
    "kind": "output_regex",
    "pattern": "(?i)\\bDONE\\b",
    "description": "Uses the kit DONE handoff; .aiek/core/handoffs.md puts the status line first, so this is ordering-independent (evidence is proven by the evidence assertion)",
    "critical": false
  }
]
```

## Mock changes
### app/auth.py
```text
USERS = {
    "alice@example.com": {"id": 1, "name": "Alice"},
    "bob@example.com": {"id": 2, "name": "Bob"},
}


def normalize_email(email: str) -> str:
    local, _, domain = email.partition("@")
    # Sub-addressing is valid: strip the "+tag" suffix but keep the local part.
    local = local.split("+")[0]
    return f"{local}@{domain}"


def find_user(email: str) -> dict:
    return USERS[normalize_email(email)]
```
### tests/test_auth.py
```text
import unittest

from app.auth import find_user, normalize_email


class AuthTest(unittest.TestCase):
    def test_plain_email(self):
        self.assertEqual(find_user("alice@example.com")["id"], 1)

    def test_plus_addressed_email_regression(self):
        self.assertEqual(normalize_email("alice+news@example.com"), "alice@example.com")
        self.assertEqual(find_user("alice+news@example.com")["id"], 1)


if __name__ == "__main__":
    unittest.main()
```

## Mock response
```text
Lane: NORMAL (bug in existing behaviour; debugging path then a small fix).

Root cause hypothesis: `normalize_email` splits the local part on `+` and keeps index `[1]`, so `alice+news` becomes `news` and the user lookup raises KeyError, surfacing as a 500. The failing test `test_plus_addressed_email_regression` reproduces it before the fix.

Fix (at the source): keep `split("+")[0]` so the base local part is preserved; the regression test now passes.

Evidence:
| Check | Command | Exit code |
| --- | --- | --- |
| regression test | python3 -m unittest tests.test_auth | 0 |
| suite | python3 -m unittest | 0 |

DONE — root cause fixed in `app/auth.py`, regression test registered, suite green.
```

## Mock response without kit
```text
I changed the split logic in app/auth.py, it should work now.
```
