# Implementation Plan: Workflow Review and Docs Copilot

**Lane**: LARGE (CLI process and outbound API boundaries)

## Summary

Extend the current Node/React app in the existing isolated implementation worktree. Reuse parser, authenticated API, snapshot, watcher and guarded editor. Canonical behavior comes from core/WORKFLOW.md; UI presents observations and explicit human attestations.

## Design

- Shared workflow derivation maps source artifacts and lane to steps and next actions; never certifies execution from prose. Revision-bound human command evidence is stored with local review state.
- Snapshot v1 gains optional bounded history with hashes and task counts; existing baselines continue to load. Atomic storage and revision checks remain.
- Add structured overview/story cards, visual workflow, review inbox, phase progress and task status filter. Existing source and raw section editor serve detailed review.
- Enable guarded Markdown-section edits for readable feature docs; all existing boundary checks remain.
- Copilot context endpoint previews selected docs for a feature or bounded project overview. Include deterministic workflow state and line-numbered, delimited untrusted docs, with manifest and truncation warnings; never include .env, code or keys.
- API adapter uses fetch Chat Completions with memory-only settings, endpoint validation, no redirects, bounded output, abort and timeout.
- Codex adapter uses installed help-verified ephemeral noninteractive read-only execution with shell disabled and user config ignored. Claude uses print, no tools, strict empty MCP, no project/user customization or hooks, no session persistence. Both run in a fresh empty temp directory; stdin carries the same previewed prompt. Detect needed flags before enabling. agy is a manual prompt handoff pending safe direct adapter verification.
- One active AI job per server, cancellation/disconnect/shutdown cleanup, no raw provider errors logged or returned. Responses include captured revision and manifest; UI labels stale context.

## Decisions Needed

No open product decisions. Defaults: API keys memory-only; text responses after completion; user explicitly chooses context and sends; project overview bounded to twenty features and 96000 document characters; history twenty rounds. CLI login and optional model use existing credentials.

## Verification

Baseline twenty-two tests pass. Add workflow/stale-evidence/history/section tests, mock HTTP provider and fake CLI process-boundary tests, browser workflow/review/task/Copilot flows. Run typecheck/lint/build, kit checker and installer dry-run, package smoke and independent review. Real credentialed provider connections are reported separately from mocked adapter proof.

## Constitution Check

Spec Kit scaffolds initialized using upstream create-new-feature/setup-plan helpers in scratch. No core, skill, adapter or Spec Kit command changes. Existing authorized temporary worktree reused; original source fingerprint captured before synchronization. Reviewer receives no author history. No publish or commits requested.
