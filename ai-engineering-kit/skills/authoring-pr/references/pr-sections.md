# Default Pull Request Sections

Used when the adapter does not name a `pr_template`. Keep the order; drop a section only when
it genuinely does not apply, and say so in one line rather than deleting it silently.

---

## Work item and branch
- **Ticket:** <id + link>
- **Branch:** `<source>` → `<target>`

## Business goal
What a user or operator can do after this that they could not before, and why that matters.
Two to four sentences, in the reader's language, no implementation vocabulary.

## Overview
- **Problem:** <what was wrong or missing>
- **Solution:** <the shape of the change, in plain language>
- **Scope limits:** <what was deliberately left out, and on whose decision>

## Main changes
Three to six bullets. Behavior first, mechanism second. A reviewer should be able to predict
what to look for in the diff after reading these.

## Architecture compliance
Which existing boundaries, chokepoints or layers this change respects, and where the new code
sits. Call out anything that deliberately deviates, and why.

## Data and migrations
Schema or data changes, how they were applied, and on which database. State explicitly what has
**not** been applied yet (shared environments, production) and whether rollback was rehearsed.

## End-user evidence
One row per behavior a reviewer is being asked to accept.

| Behavior to review | Evidence at this commit |
|---|---|
| <...> | <link to test / trace id / log excerpt / image of the real thing> |

**Missing:** <behaviors with no evidence yet, named explicitly>

Never fabricate an image, a log line or a run to fill a row.

## Verification and limits
The verification output as it was produced, including failures, skips and blockers:

```
<command>
<result: counts, exit code, blockers>
```

**Not verified:** <what, and why — environment, mocks, missing access, time>

## Author self-review and cross-review
- **Author:** what you checked yourself, and what you found and fixed.
- **Independent review:** state, findings, and whether they are resolved. "Not yet reviewed" is
  an acceptable value; "approved" is not something the author writes.

## Related changes and merge order
Open pull requests touching the same files, whether they merge before or after this one, and
what must be re-run after they land. "Checked, no overlap" is a valid entry; silence is not.

## Deployment, post-deploy checks and rollback
What has to happen at deploy time, what to look at afterwards to know it worked, and how to
roll back. If nothing deploys yet, say so and name the precondition.

## Configuration changes
Environment keys to **add** and to **remove**, by name only. Never put a secret value in a
description. If none, write "none".

## Release note
The exact sentence a user will read in the changelog. One or two sentences, their language, no
internal terms.
