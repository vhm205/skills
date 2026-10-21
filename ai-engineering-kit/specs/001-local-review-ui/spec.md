# Feature Specification: Local Review UI

**Feature Branch**: `001-local-review-ui`  
**Created**: 2026-10-17  
**Status**: Approved for implementation

## User Scenarios & Testing

### User Story 1 - Understand a feature (Priority: P1)

Inspect scope, declared lane, tasks and sources without opening every document.
Independent Test: Select a fixture feature, inspect stories, criteria, tasks and exact sources.
Acceptance: Missing/unsupported files remain readable with warnings; planned PASS or ticked tasks never imply verified READY or DONE; external edits refresh within two seconds.

### User Story 2 - Review changes (Priority: P1)

Save a local baseline of what was read, including uncommitted docs.
Independent Test: Save baseline, modify/add/delete documents, restart and inspect diffs.
Acceptance: No baseline is explicit; worktrees have separate baselines; saving rejects unseen edits.

### User Story 3 - Record a decision (Priority: P1)

Edit Decisions Needed in plan or Clarifications in spec, preview diff and save.
Independent Test: Compare entire file bytes before/after editing one section.
Acceptance: Preserve other bytes; stale saves conflict and retain draft; unsupported sections stay read-only; never approve a gate automatically.

### User Story 4 - Packaged launch (Priority: P1)

Launch built package without cloning, building or installing project dependencies.
Independent Test: Run npm tarball in a scratch project with spaces in its path.
Acceptance: Assets load; default busy port falls back, explicit busy port fails; shutdown closes listener/watcher.

### Edge Cases

Missing kit/specs, empty docs, duplicate headings, UTF-8/CRLF, atomic saves, disconnects, malformed snapshots, symlinks, unsafe paths and executable Markdown.

## Requirements

- **FR-001**: Vietnamese overview, decisions, changes, tasks, evidence and source views with live refresh.
- **FR-002**: Canonical docs remain authoritative; distinguish declared facts, observations and unknown evidence.
- **FR-003**: One persistent baseline per canonical project/worktree and feature, stored outside project.
- **FR-004**: Supported section edits use diff preview, whole-file hash checks and guarded atomic replacement.
- **FR-005**: Loopback-only server, authenticated APIs, same-origin writes, no arbitrary file access or script execution.
- **FR-006**: Prebuilt npm CLI/server/UI plus kit assets; preserve installer; package version matches manifest.
- **FR-007**: No agent/command execution, automatic approval, AI API key or registry publication in v1.

### Key Entities

Project, feature, artifact, section, task, source reference, baseline and file diff.

## Success Criteria

- **SC-001**: Locate scope, decisions and evidence limitations in one minute (manual user measurement).
- **SC-002**: Local edits reflected within two seconds in browser integration checks.
- **SC-003**: Stale writes preserve observed external changes; rejected paths cannot be written.
- **SC-004**: Packaged launch and review flows pass automated tests.

## Assumptions

One project per process; Node >=22.12; Git optional; UI needs no runtime internet after install. External editors cannot be fully locked against the final replacement race.
