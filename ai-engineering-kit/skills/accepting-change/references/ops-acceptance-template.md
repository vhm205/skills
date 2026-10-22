# Ops Acceptance — <change / ticket id>

**Date:** YYYY-MM-DD · **Change:** <what was altered> · **Environment:** <where>
**Performed by:** <person> · **Approver:** <person>

Acceptance is incomplete while any of the three parts below is missing. Say which part is
missing rather than declaring the change accepted.

---

## 1 · Post-change smoke

Confirm the running system, not the exit code of the command you ran.

| # | Check | How you looked | Expected | Result |
|---|---|---|---|---|
| 1 | Services are up | <command / console> | <all expected units running> | ☐ |
| 2 | Health endpoint answers | <command> | <status + body shape> | ☐ |
| 3 | **The change is actually live** | <compare running artifact identity against the intended one> | <they match> | ☐ |
| 4 | Dependent path still works | <a request that exercises it end to end> | <...> | ☐ |

Check 3 is the one that is usually skipped and the one that is usually wrong. "The command
succeeded" is not evidence that the new artifact is what is serving traffic.

```
<paste the command and its real output here>
```

---

## 2 · Before / after comparison

Recorded **before** the change, repeated after. Anything that moved and was not supposed to is
a finding.

| Signal | Before | After | Expected to change? | Note |
|---|---|---|---|---|
| <artifact identity / version> | <...> | <...> | yes | |
| <error rate> | <...> | <...> | no | |
| <latency p95> | <...> | <...> | no | |
| <resource usage> | <...> | <...> | <...> | |
| <row/record counts on touched data> | <...> | <...> | no | |

If no "before" was recorded, say so. A comparison invented after the fact is not a comparison.

---

## 3 · Rollback rehearsal

Required for anything hard to reverse: cutovers, schema or infrastructure migrations, registry
or release changes, anything that touches shared or production state.

- **Reversing this means:** <the actual steps>
- **Rehearsed in:** <isolated environment, when>
- **Rehearsal result:** <what came back, how long it took, what was lost>

```
<paste the rehearsal output here>
```

- **Not reversible by rollback:** <data written, messages sent, artifacts published, caches
  warmed elsewhere — name them>
- **Point of no return:** <the step after which rollback stops being an option>

A rollback that was planned but never performed is recorded as **not rehearsed**, and the
change is not accepted on that basis.

---

## 4 · Thresholds and baseline

For performance or capacity work:

| Metric | Threshold agreed | Measured before | Measured after | Pass |
|---|---|---|---|---|
| <...> | <value + unit + conditions> | <...> | <...> | ☐ |

Thresholds that are now met go into the project's baseline so a later regression is visible.

---

## 5 · Result

**Smoke:** ☐ · **Before/after:** ☐ · **Rollback rehearsed:** ☐

**Outstanding:** <one line per gap, with what it blocks>

**Approver sign-off:** `APPROVED` / `REJECTED` — <name, date>
