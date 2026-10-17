---
name: ai-engineering-kit
description: Project-agnostic engineering workflow combining Spec Kit (specifications, plans, tasks) and disciplined execution skills (shaping, execution, verification, review, systematic debugging, worktrees, parallelism). Use when running structured feature development, bug fixes, or complex refactors with coding agents.
---

# AI Engineering Kit

A unified, project-agnostic workflow for coding agents (Claude Code, OpenAI Codex, Antigravity, etc.) integrating **Spec Kit** planning discipline with **Superpowers** execution skills.

---

## 1. Core Workflow & Lanes

Every change request (feature, bug, refactor) follows a lane determined by scope:

```text
Change request ─► unclear how? ─► shaping-feature ─► Feature Brief ─┐
               └► unclear whether? ─► Spec Kit assess ──────────────┤
                                                                    ▼
                            classify lane (.aiek/core/classification.md)
   SMALL  ─► execute ─► verify ─► review ─► DONE
   NORMAL ─► specify ─► plan ─► tasks ─► READY TO BUILD ─► execute ─► verify ─► review ─► DONE
   LARGE  ─► research ─► specify ─► clarify ─► plan ─► NEEDS DECISION ─► tasks ─► analyze
             ─► READY TO BUILD ─► worktree ─► execute ─► verify ─► independent review ─► DONE
```

---

## 2. Lane Rules

- **SMALL** (few files, clear fix): `executing-task` ─► `verifying-change` ─► `reviewing-change` (self-review) ─► `DONE`.
- **NORMAL** (standard feature/refactor): Spec Kit `specify` ─► `plan` ─► `tasks` ─► `READY TO BUILD` ─► implement ─► `verifying-change` ─► `reviewing-change` ─► `DONE`.
- **LARGE** (multi-component, architecture risk): Spec Kit `research` ─► `specify` ─► `clarify` ─► `plan` ─► `NEEDS DECISION` ─► `tasks` ─► `analyze` ─► worktree isolation (`using-worktrees`) ─► parallel execution (`parallel-development`) ─► independent review ─► `DONE`.

---

## 3. Strict Operating Invariants

1. **One Source of Truth**: After `specify`, artifacts in `specs/<feature>/` own all plans and tasks. Never create a separate secondary task list or plan file.
2. **Mandatory Evidence**: No completion claim (`DONE`) without fresh, verified evidence from tests, linters, or manual verification (`verifying-change`).
3. **Structured Handoffs**: Always use `BLOCKED`, `NEEDS DECISION`, or `DONE` when yielding execution or handing off to human developers.
4. **Adapter Contract**: Build, test, and lint commands must strictly conform to `.aiek/adapter.md`.
5. **No Competing Workflows**: Do not activate Superpowers or conflicting planning plugins concurrently in the same session.

---

## 4. Setup in Target Project

To initialize this kit with full workflow and Spec Kit integration in any project:

```bash
scripts/install.sh . --speckit
```
