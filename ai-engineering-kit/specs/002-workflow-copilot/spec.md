# Feature: Workflow Review and Docs Copilot

## Summary

Help the human review each workflow output, see current and next checkpoints, track declared task progress, and ask questions grounded in project documents.

## User Scenarios & Testing

### User Story 1 - Review the latest workflow output (Priority: P1)

When a slash command creates or changes documents, the user sees an updated review inbox, affected workflow stages and source-backed summaries. Saving a review baseline records a local review round. Users can edit document sections with conflict protection.

### User Story 2 - Understand current and next steps (Priority: P1)

The UI presents the canonical workflow, available/changed/reviewed documents, pending clarifications, completed and remaining tasks by phase, and a concrete next action. Large lanes retain analyze, isolation and independent review requirements. Human-reported command evidence is distinct from UI-verified execution and becomes stale when the feature revision changes.

### User Story 3 - Ask a docs copilot (Priority: P2)

Users choose Codex CLI, Claude CLI or an OpenAI-compatible endpoint and model. They preview the bounded context before sending, ask follow-up questions and cancel an active request. Responses carry context sources and revision; old answers are visibly stale. A project scope can include multiple features with explicit truncation. API keys are never persisted or echoed. agy receives a copyable handoff prompt until a tool-free adapter is verified.

## Functional Requirements

- FR-001: Watch external document changes; show pending review and semantic summaries with source links, not only raw Markdown.
- FR-002: Preserve canonical lane workflow and expose uncertainty about unobserved commands.
- FR-003: Keep at most twenty review rounds and command attestations outside the project. Reject stale revisions.
- FR-004: Support guarded edits for ordinary Markdown sections, preserving surrounding bytes and rejecting structural corruption.
- FR-005: Copilot launches allowlisted CLI binaries without a shell, from an empty temporary directory, with tool/customization restrictions and bounded time/output. Never execute workflow commands from chat.
- FR-006: HTTP chat uses an explicit HTTPS or loopback HTTP endpoint; disable redirects; bound request/response and timeout. Settings are session-memory only. No real provider call occurs before Send.
- FR-007: Show missing binaries, unsupported versions, auth/provider failures and cancellation without exposing prompts/keys in errors.
- FR-008: Existing launch/auth/snapshot/editor/package behavior remains compatible.

## Acceptance Scenarios

1. External plan/spec/tasks edits update review counts and summaries without discarding an open draft.
2. New tasks docs do not imply analyze/verification/review passed. Saved review is distinct from command evidence.
3. Phase progress and completed filters agree with checkboxes; source links open relevant content.
4. A full-section edit retains conflict and Markdown-boundary protection.
5. Mock compatible API and fake CLI integrations receive only previewed context; cancellation/timeout/error paths terminate work and do not expose credentials.
6. Browser flows cover workflow, review rounds, progress filters, copilot context/settings/cancel and source access at supported widths.

## Scope

Local review and advisory Q&A. CLI adapters create new ephemeral questions, not attachments to existing interactive sessions. No automatic gate approvals, task execution or project writes by Copilot. Real provider credentials are configured by the user.
