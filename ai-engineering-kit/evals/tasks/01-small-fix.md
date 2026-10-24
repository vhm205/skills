# small-fix

- id: small-fix
- title: Small fix — typo in the signup email
- critical: true
- timeout_s: 600
- lane: SMALL

## Prompt
```text
The signup email has a typo — fix it.
```

## Setup
### src/emails/signup.ts
```text
export const signupEmail = {
  subject: "Welcom aboard",
  body: "Thanks for signing up. Please confirm your email address.",
};
```
### README.md
```text
# Demo app

A tiny project used by the kit behaviour fixture.
```

## Assertions
```json
[
  {
    "id": "lane-small",
    "kind": "output_regex",
    "pattern": "(?i)lane[^\\n]{0,80}small",
    "description": "States the SMALL lane before acting",
    "critical": true
  },
  {
    "id": "evidence-present",
    "kind": "output_regex",
    "pattern": "(?i)(evidence|verification)",
    "description": "Reports verification/evidence for the change",
    "critical": true
  },
  {
    "id": "evidence-table",
    "kind": "output_regex",
    "pattern": "(?is)\\|[^\\n]*(command|check|verification|exit)[^\\n]*\\|",
    "description": "DONE report carries a command/exit-code evidence table",
    "critical": false
  },
  {
    "id": "typo-fixed",
    "kind": "file_contains",
    "path": "src/emails/signup.ts",
    "pattern": "Welcome aboard",
    "description": "The typo is actually fixed in the file",
    "critical": true
  },
  {
    "id": "typo-gone",
    "kind": "file_not_contains",
    "path": "src/emails/signup.ts",
    "pattern": "Welcom aboard",
    "description": "The misspelling no longer exists",
    "critical": true
  },
  {
    "id": "changed-expected-file",
    "kind": "changed_glob",
    "glob": "src/emails/signup.ts",
    "description": "Only the target file needed changing",
    "critical": true
  },
  {
    "id": "no-spec-for-small",
    "kind": "new_glob_absent",
    "glob": "specs/**",
    "description": "No Spec Kit artifacts for a Small change",
    "critical": true
  },
  {
    "id": "done-present",
    "kind": "output_regex",
    "pattern": "(?i)\\bDONE\\b",
    "description": "Uses the kit DONE handoff; .aiek/core/handoffs.md puts the status line first, so this is ordering-independent (evidence is proven by the Checks table assertion)",
    "critical": false
  },
  {
    "id": "kit-files-untouched",
    "kind": "unchanged_glob",
    "glob": ".aiek/**",
    "description": "The installed kit files are not modified",
    "critical": false
  }
]
```

## Mock changes
### src/emails/signup.ts
```text
export const signupEmail = {
  subject: "Welcome aboard",
  body: "Thanks for signing up. Please confirm your email address.",
};
```

## Mock response
```text
Lane: SMALL (single-file copy fix, no behaviour change; adapter verify command is auto).

Fixed the misspelling in `src/emails/signup.ts` ("Welcom" → "Welcome"). No spec or plan artifacts are needed for a Small change.

Evidence:
| Check | Command | Exit code |
| --- | --- | --- |
| typo fixed | grep -n "Welcome aboard" src/emails/signup.ts | 0 |
| misspelling gone | ! grep -n "Welcom aboard" src/emails/signup.ts | 0 |
| scope | git diff --name-only | 0 |

DONE — one file changed, no behaviour change beyond the copy.
```

## Mock response without kit
```text
Fixed the typo: "Welcom" is now "Welcome".
```
