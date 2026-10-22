# Ops Evidence Sheet — <change / ticket id>

Fill the **Planned evidence** column *before* doing the work. Fill **Observed** afterwards, with
real output. A row with no observation is not done.

**Change:** <what> · **Environments touched:** <list, in the order you will touch them>

---

## 1 · Evidence plan

| # | Claim this change makes | Planned evidence | Observed |
|---|---|---|---|
| 1 | <the artifact is built from this revision> | <identity of published artifact == source revision> | |
| 2 | <the running system serves the new artifact> | <running instance identity / start time vs artifact> | |
| 3 | <the deploy check passes> | <command + expected exit> | |
| 4 | <the threshold is met> | <metric, value, unit, conditions> | |
| 5 | <nothing else moved> | <before/after signals> | |

---

## 2 · Artifact identity

| Artifact | Intended revision | Published as | Running instance reports | Match |
|---|---|---|---|---|
| <application image> | <sha> | <tag/digest> | <what the live system reports> | ☐ |
| <side service> | | | | ☐ |
| <generated data / index> | | | | ☐ |

List **every** artifact group the change touches. An environment is not one thing: the
application, its side services, its data and its generated indexes are refreshed independently,
and patching one leaves the others stale.

```
<paste the commands and real output that establish identity>
```

---

## 3 · Measurement (capacity and performance work)

| Phase | Command | Result | Meets threshold? |
|---|---|---|---|
| Before | <...> | <number + unit> | **no** ← this must be observed |
| After | <...> | <number + unit> | yes |

**Threshold:** <value, unit, under what conditions, agreed with whom>

A threshold first observed as met is not evidence. Measure before, see it fail, then change.

---

## 4 · Reversibility

| Step | Reversible? | How to reverse | Rehearsed |
|---|---|---|---|
| <...> | yes | <...> | n/a |
| <...> | **no** | <...> | ☐ |

**Point of no return:** <which step>
**Not undone by rollback:** <data written, artifacts published, messages sent, caches warmed
elsewhere>

Rehearsal output:

```
<paste it>
```

---

## 5 · Configuration

Names only. Never a value, never a secret.

| Key | Action | Read by | Default if absent |
|---|---|---|---|
| <NAME> | add / remove | <file:symbol> | <value or "fails at startup"> |

---

## 6 · What was not verified

| Claim | Why not verified | What it leaves open |
|---|---|---|
| <...> | <no access / no environment / not reproducible locally> | <...> |

This section being empty is a claim in itself. Fill it honestly.
