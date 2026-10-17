# Root Cause Tracing

Bugs usually surface far from where they start. Trace backward until you reach the original
trigger, then fix there.

1. **Observe the symptom.** Where exactly does the wrong value or behavior appear?
2. **Find the immediate cause.** Which line produced it?
3. **Ask "who called this, with what?"** Walk one level up the call chain. Note the value
   passed at each level.
4. **Keep going** until you find where a correct value first became incorrect, or where an
   invalid input entered the system.
5. **Fix at that point.** Then decide whether a guard at the boundary where the bad value
   entered would stop the whole class of bug (defense in depth). Add it only if it is cheap
   and clear.

When manual tracing stalls, add temporary instrumentation (log the value and a stack trace
before the failing operation), run once, read the output, then remove the instrumentation.

For a test that pollutes shared state, bisect: run test files one at a time (or halve the set
repeatedly) until the polluting test is found.
