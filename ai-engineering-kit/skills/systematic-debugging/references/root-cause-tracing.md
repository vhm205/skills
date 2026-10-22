# Root Cause Tracing

Bugs usually surface far from where they start. Trace backward until you reach the original
trigger, then fix there.

1. **Observe the symptom.** Where exactly does the wrong value or behavior appear?
2. **Find the immediate cause.** Which line produced it?
3. **Ask "who called this, with what?"** Walk one level up the call chain. Note the value passed
   at each level.
4. **Keep going** until you find where a correct value first became incorrect, or where an
   invalid input entered the system.
5. **Fix at that point.** Then decide whether a guard at the boundary where the bad value
   entered would stop the whole class of bug (defense in depth). Add it only if it is cheap and
   clear.

When manual tracing stalls, add temporary instrumentation (log the value and a stack trace
before the failing operation), run once, read the output, then remove the instrumentation.

For a test that pollutes shared state, bisect: run test files one at a time (or halve the set
repeatedly) until the polluting test is found.

---

## When there is no error to trace

The hardest bugs produce no exception, no stack trace and no red test. Something simply does
not happen. Five families cover most of them — check each before concluding "it works on my
machine".

### 1. The patch exists but is not running

The code is correct and is not the code being executed. Caused by a process that was never
restarted, an image that was never rebuilt, a cached asset still served under its old version,
a migration never applied, or a generated index never refreshed.

**Check:** compare the running instance's start time against the file's timestamp, and compare
artifact identities. **Never check by starting a new process** — a fresh process loads the new
code regardless of what the serving process is running, so it always confirms you.

An environment is several independent artifact groups. Refreshing one leaves the rest stale.

### 2. A fail-open handler swallowed the error

A broad `catch` / `except` around the new code turns a real failure — a syntax error in a query,
a type mismatch, a missing field — into a silent no-op. The feature "does nothing" and nothing
complains.

**Check:** search the logs for the handler's own failure message before trusting any "verified"
claim. Then narrow the handler, or let it raise.

**Rule this produces:** a statement that is only parsed by the real dependency — a query, a
schema, a template — needs at least one test that runs it against the real dependency. A test
with a fake one proves only that your string was built.

### 3. The write side and the read side disagree on the key

One component writes under one name, another reads under a different one. Both succeed. Nothing
links them. Common with event names, feature keys, config names and column aliases.

**Check:** list what is emitted and what is listened for, and diff the two sets. Names emitted
that nobody consumes are the bug. Fix by bridging through the system's existing alias
mechanism, not by renaming one end and leaving the other.

### 4. "Missing at the read layer" is not "missing at the source"

A reader that filters, paginates or projects can hide data that is present. Concluding the
source is empty sends the fix to the wrong place entirely.

**Check:** open the source and count, before stating anything about what it contains.

### 5. A generated value was composed instead of looked up

Where a model, a template or a user supplies a value that should have been resolved from
authoritative data, the result is plausible and wrong — an identifier that does not exist, a
code for the wrong record.

**Check:** the same operation twice with two different values for an identifier that should be
fixed. The rule to restore: the caller decides *whether* to act, the system decides *with what
data*.

---

## Intermittent bugs

One failure in five is a different problem from a reproducible one, and the usual loop —
reproduce, change, re-run — will tell you a change worked when it did not.

1. **Establish the rate first.** Run it enough times to know whether it is 1-in-5 or 1-in-50.
   Without a rate you cannot tell a fix from luck.
2. **Capture a failing run and a passing run** under the same conditions, and diff everything
   you can: timings, ordering, which instance served it, which values were cached.
3. **Suspect what varies between runs**: concurrency and ordering, time and timezone boundaries,
   randomized iteration order, retries, connection reuse, several instances where you assumed
   one, leftover state from an earlier run.
4. **Re-run the same number of times after the fix.** A single pass proves nothing at a 1-in-5
   rate; neither does five passes. Match the sample to the rate.
5. If it cannot be made to fail on demand, add instrumentation that survives until it does
   rather than guessing at a cause.
