# Author Self-Review Checklist

Run this before asking anyone else to look. You are looking for the things a reviewer should
never have to spend their attention on.

## The description against the ticket

- [ ] Every acceptance criterion in the ticket appears somewhere in the description.
- [ ] Nothing is claimed that the ticket did not ask for. Extra work is named as extra.
- [ ] Anything the ticket listed as out of scope is still out, or the deviation is stated.
- [ ] Open questions that were never answered are listed, not quietly resolved.

## The description against the diff

- [ ] Each "main change" bullet is visible in the diff.
- [ ] Each file in the diff is explained by some bullet. Unexplained files are either removed
      from the change or added to the description.
- [ ] The architecture section matches where the code actually went.
- [ ] Configuration keys listed match the keys the diff actually reads.
- [ ] Migration or data claims match the files actually added.

## The diff itself

- [ ] No debug output, temporary logging, or commented-out code from this session.
- [ ] No reformatting of lines the change did not need to touch.
- [ ] No files committed by accident: local config, credentials, editor state, build output.
- [ ] No secret, token or password in any added line.
- [ ] Whitespace / diff sanity check runs clean.
- [ ] New tests actually run in the lane that gates this change, not only locally.

## The evidence

- [ ] Every number in the description can be traced to a command run in this session.
- [ ] Failures and skips are present, not filtered out.
- [ ] Every evidence link resolves at **this** commit, not at a branch name that will move.
- [ ] Behaviors with no evidence are listed under "missing", not omitted.

## The prose

- [ ] The goal and release note read as if written for someone outside the team.
- [ ] No sentence promises a result the evidence does not show.
- [ ] After any rewrite pass, numbers, identifiers and terminology still match the original.

## Last question

> If a reviewer accepted this description without reading the code, what would they wrongly
> believe?

Write the answer into the limits section.
