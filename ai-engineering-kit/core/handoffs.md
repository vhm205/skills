# Human Handoffs

Agents may give concise progress updates and ask discovery questions. Do not ask permission
to continue authorized work or ask questions answered by the code, spec or adapter.

They hand off to a human in exactly three situations, using exactly these shapes. Each report
starts with its status word on the first line so a human can triage a queue of them quickly.

## BLOCKED

Use when continuing would mean guessing, causing damage, or acting outside your authority.

Typical causes: missing access or credentials; an operation requiring authorization not
already granted (such as destructive work, deploy, publish or send); required review is
unavailable; the environment is broken; three fix attempts failed
(`systematic-debugging`).

```markdown
BLOCKED: <one line>

**Blocker:** <what stops you, concretely>
**Attempted:** <what you tried, with the evidence (commands, errors)>
**Required:** <the exact thing a human must do or provide to unblock>
**State left behind:** <branch/worktree, uncommitted changes, anything half-done>
```

## NEEDS DECISION

Use when a product, architecture or trade-off choice changes what gets built and is not yours
to make. Do not use it for choices with a conventional default: make those yourself and list
them as rulings in DONE.

```markdown
NEEDS DECISION: <the question in one line>

**Context:** <why this came up; link the spec/plan section>

| Option | Trade-offs | Cost if wrong |
|---|---|---|
| A. ... | ... | ... |
| B. ... | ... | ... |

**Recommendation:** <option and the one-sentence reason>
**Decision required:** <exactly what the human must choose; what you will do for each answer>
```

After the decision, record it where it belongs (the spec or plan for Normal/Large) before
continuing, so the artifact stays the source of truth.

## DONE

Use only after `verifying-change` has produced fresh evidence. "Should work" is not DONE.

```markdown
DONE: <one line>

**Summary:** <what changed and why, 2-4 lines; lane; spec link if any>
**Files changed:** <list, or `git diff --stat` output>
**Checks run:**
| Check | Command | Result |
|---|---|---|
| tests | `...` | 142 passed, 0 failed |
| lint / typecheck | `...` | exit 0 |
**Verification evidence:** <how each acceptance criterion / the original symptom was confirmed>
**Rulings made:** <decisions you took without asking, each: what, why, cost if wrong; or "none">
**Review:** <self-review or reviewer; findings fixed; findings deferred>
**Remaining risks:** <what was not verified and why; follow-ups>
```

For Small changes, collapse DONE to a few lines: change, check evidence, self-review and any
remaining risk. Omit empty sections. This preserves the gate without a full report for a typo.

## Concurrency

Agents may run concurrently (separate worktrees or independent tasks). Their reports go to the
human one at a time, in a queue: the human reviews sequentially and agents do not wait on each
other's reviews unless their tasks depend on each other.
