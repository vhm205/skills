# review-diff

- id: review-diff
- title: Review — diff removes a tenant authorization check
- critical: true
- timeout_s: 600
- lane: REVIEW

## Prompt
```text
Review this diff before I merge. The change is in change.diff.
```

## Setup
### src/api/orders.py
```text
from fastapi import APIRouter, Depends, HTTPException

from app.auth import current_user

router = APIRouter()


@router.get("/orders/{order_id}")
def get_order(order_id: str, user=Depends(current_user)):
    tenant_id = user.tenant_id
    order = load_order(order_id)
    if order is None:
        raise HTTPException(status_code=404)
    return order
```
### change.diff
```diff
diff --git a/src/api/orders.py b/src/api/orders.py
index 1111111..2222222 100644
--- a/src/api/orders.py
+++ b/src/api/orders.py
@@ -8,10 +8,8 @@ router = APIRouter()
 @router.get("/orders/{order_id}")
 def get_order(order_id: str, user=Depends(current_user)):
-    tenant_id = user.tenant_id
     order = load_order(order_id)
-    if order is None or order["tenant_id"] != tenant_id:
+    if order is None:
         raise HTTPException(status_code=404)
     return order
```
### README.md
```text
# Demo orders API
```
### app/auth.py
```text
class User:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id


def current_user() -> User:
    return User("tenant-a")
```

## Assertions
```json
[
  {
    "id": "finding-file-line",
    "kind": "output_regex",
    "pattern": "[\\w./-]+\\.(py|ts|tsx|js|jsx|go|rb|java|kt):\\d+",
    "description": "Findings are anchored to file:line",
    "critical": true
  },
  {
    "id": "severity",
    "kind": "output_regex",
    "pattern": "(?i)\\b(critical|high|blocker|severe)\\b",
    "description": "Findings carry a severity",
    "critical": true
  },
  {
    "id": "authorization-explained",
    "kind": "output_regex",
    "pattern": "(?i)(authoriz|authoris|tenant|permission|access control|authz|IDOR)",
    "description": "The authorization regression is named explicitly",
    "critical": true
  },
  {
    "id": "fix-suggested",
    "kind": "output_regex",
    "pattern": "(?i)(fix|restore|add|re-?introduce|suggest)",
    "description": "A concrete fix is suggested",
    "critical": true
  },
  {
    "id": "no-blind-approval",
    "kind": "output_not_regex",
    "pattern": "(?im)^\\s*(LGTM|approved|ship it)[.!]?\\s*$",
    "description": "Does not blindly approve the diff",
    "critical": true
  }
]
```

## Mock changes

## Mock response
```text
Findings (reviewing-change):

1. CRITICAL — `src/api/orders.py:11` (in the diff hunk `@@ -8,10 +8,8 @@`): the change drops the tenant check `order["tenant_id"] != tenant_id`, so any authenticated user can read another tenant's order by id. This is an IDOR / broken access control regression.
   Suggested fix: restore the `tenant_id` comparison and return 404 (not 403) when it does not match.

2. HIGH — `src/api/orders.py:9`: the removed `tenant_id = user.tenant_id` line also makes the intent of the check disappear; re-introduce it together with the check.

I did not run the test suite (reviewers do not replace verification); the change is not ready to merge until the authorization check is restored and covered by a test.
```

## Mock response without kit
```text
Looks fine to me. The diff simplifies the endpoint and cleans up an unused variable.
```
