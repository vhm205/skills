# Implementation Plan: Local Review UI

**Branch**: `001-local-review-ui` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)
**Lane**: LARGE (local authentication and document write boundary).

## Summary

Implement user-approved conversational plan: single npm package, Node HTTP/TypeScript, React/Vite, remark/GFM, chokidar and diff. Snapshot baseline outside project, SSE refresh and guarded section edits. No open decisions.

## Technical Context

Node >=22.12; npm lockfile; Vitest, Playwright and existing Python checks. Runtime in src/, UI in ui/, tests in tests/, output in dist/. Libraries provide source positions, GFM rendering, cross-platform watching and text diffs. No database or workflow engine.

## Constitution Check

No initialized constitution. Repository AGENTS.md and canonical core apply. Upstream Spec Kit initialized offline in scratch; spec/plan generated through upstream helpers/templates, then populated for this feature. Native checkout outside writable roots; authorized temporary Git worktree used instead. Baseline: checker and seven Python tests pass. Independent review required before completion.

## Interfaces and Behavior

Read APIs identify feature/artifact/section through server IDs. Fragment token exchange establishes same-origin session cookie; all APIs require it, writes validate Origin. Section updates take replacement text and expected whole-file hash, return 409 on stale content. Snapshot save takes displayed feature revision to reject unseen changes. Serialize writes; validate path/inode/hash before atomic rename; preserve mode and unrelated bytes. External uncooperative writers retain a narrow final race, disclosed to users.

Snapshot storage uses platform user data directory (AIEK_DATA_DIR override for tests). One baseline per canonical project/worktree and feature. Source index is disposable. UI does not certify gate completion from prose or checked tasks. Unsupported structures remain readable.

## Verification

Parser/storage/security unit and integration tests; browser review/edit/conflict/responsive flows; npm tarball CLI/assets/port/shutdown tests; build/typecheck/lint; checker, installer dry-run, Python tests; Node 22 and 24 launch where available; independent diff review.
