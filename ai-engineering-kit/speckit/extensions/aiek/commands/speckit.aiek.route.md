---
description: "Classify a change request (shape / assess / Small / Normal / Large) and name the next step"
---

## User Input

```text
$ARGUMENTS
```

## Goal

Decide which path of the AI Engineering Kit workflow this change request takes, state it in
one line, and name the next command or skill. Do **not** write a spec, plan or code here.

## Steps

1. Read `.aiek/core/classification.md` and `.aiek/adapter.md` (if present). Read just enough of
   the codebase to judge the change's reach (files, layers, risk areas).
   If this is a new project/BRD rather than one change, route to the new-project path in
   `.aiek/core/WORKFLOW.md`: bootstrap, `shaping-project`, constitution, roadmap, approval,
   then classify its first slice. Stop routing; do not label the whole project LARGE.
2. **Discovery check** (first match wins):
   - Unclear *whether* to build it (value, priority, cost) → recommend the idea assessment
     (`__SPECKIT_COMMAND_ASSESS_INTAKE__` if the `assess` extension is installed).
   - Unclear *how* it should work (problem, users, behavior) → recommend the
     `shaping-feature` skill, which produces a Feature Brief.
3. Otherwise **classify the lane** with the hard triggers and the scoring table in
   `classification.md`. Pick the heavier lane when in doubt.
4. Output exactly:

   ```markdown
   Lane: <SHAPE | ASSESS | SMALL | NORMAL | LARGE> (<one-line reason>)
   Hard triggers: <none | list>
   Next: <one step>
   ```

   where Next is:
   - SHAPE → "Use the `shaping-feature` skill"
   - ASSESS → the installed assessment command; if unavailable, a short assessment in chat
   - SMALL → "Use the `executing-task` skill (no Spec Kit artifacts needed)"
   - NORMAL → `__SPECKIT_COMMAND_SPECIFY__ <request or Feature Brief>`
   - LARGE → "Research open unknowns, then `__SPECKIT_COMMAND_SPECIFY__`; plan with a decision gate"
5. Stop. Do not proceed to the next step unless the user's input explicitly asked you to.
