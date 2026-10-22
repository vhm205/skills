# Acceptance Sheet — <change / ticket id>

**Date:** YYYY-MM-DD · **Build / commit:** <sha> · **Environment:** <where this was checked>
**Checked by:** <person> · **Approver:** <person>

Legend: `☐ not checked` · `✅ pass` · `❌ fail` · `⚠️ pass with condition` · `⊘ not checkable`

> A case that could not be checked is marked `⊘` **with a reason**. Never leave a result blank
> and never mark it passed.

---

## 0 · Preconditions

| # | What must be true before checking | Done |
|---|---|---|
| P1 | <migration applied / data seeded / feature enabled / account available> | ☐ |
| P2 | <the build under test is the one actually running — how you confirmed it> | ☐ |

---

## 1 · Smoke — stop if any of these fail

### S-1 · <one-line name> *(criterion: AC-xx)*
**Why it matters:** <what is broken for the user if this fails>

| Step | Action | Real data to enter |
|---|---|---|
| 1 | <...> | <the actual text / value / file, not a placeholder> |
| 2 | <...> | <...> |

**Expected:** <an observation: what appears, what is returned, what is not written>
**Result:** ☐ **Note:** <what was actually seen, if it differs>

---

## 2 · Full

### F-1 · <name> *(criterion: AC-xx)*
**Why it matters:** <...>

| Step | Action | Real data to enter |
|---|---|---|
| 1 | <...> | <...> |

**Expected:** <...>
**Result:** ☐ **Note:**

### F-2 · <boundary values> *(criterion: AC-xx)*
Check the first value, the last value, and one just outside the range. One row each.

| Value | Expected | Result |
|---|---|---|
| <first in range> | <accepted> | ☐ |
| <last in range> | <accepted> | ☐ |
| <just outside> | <rejected, with the exact message> | ☐ |

### F-3 · <error path> *(criterion: AC-xx)*
**Expected when the dependency is slow, down, or errors:** <...>
**Result:** ☐ **Note:**

---

## 3 · Regression — must still work

| # | What | Expected | Result |
|---|---|---|---|
| R-1 | <existing behavior near the change> | <unchanged> | ☐ |

---

## 4 · Machine steps that were skipped

Copied from the scenario run. These fall through to this sheet; they are not passes.

| Step | Why it could not run | Checked here as |
|---|---|---|
| <...> | <missing dependency / no credentials / not automatable> | <case id, or "not checked"> |

---

## 5 · Result

| | Count |
|---|---|
| Pass | |
| Fail | |
| Pass with condition | |
| Not checked / not checkable | |

**Outstanding:** <every ❌, ⚠️ and ⊘, one line each, with what it blocks>

**Approver sign-off:** `APPROVED` / `REJECTED` — <name, date>

A mixed result is reported as mixed. Do not summarize it as a pass.
