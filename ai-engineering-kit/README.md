# AI Engineering Kit

A single, project-agnostic workflow for small teams using coding agents (Claude Code, Codex, Antigravity, DeepSeek-based agents, …).

- **Discovery** (`shaping-feature`): Turns vague ideas into a Feature Brief, then stops.
- **Spec Kit**: Owns requirements, plans, and tasks. Once specified, it is the only source of truth.
- **Execution skills** (adapted from Superpowers): Own discipline: isolation, debugging, parallelism, verification, and review.
- **Humans**: Use BLOCKED, NEEDS DECISION, or DONE for handoffs; discovery and progress updates remain allowed.

```text
Change request ─► unclear how? ─► shaping-feature ─► Feature Brief ─┐
               └► unclear whether? ─► Spec Kit assess ──────────────┤
                                                                    ▼
                            classify lane (core/classification.md)
   SMALL  ─► execute ─► verify ─► review ─► DONE
   NORMAL ─► specify ─► plan ─► tasks ─► READY TO BUILD ─► execute ─► verify ─► review ─► DONE
   LARGE  ─► research ─► specify ─► clarify ─► plan ─► NEEDS DECISION ─► tasks ─► analyze
             ─► READY TO BUILD ─► worktree ─► execute ─► verify ─► independent review ─► DONE
```

## Layout

```text
ai-engineering-kit/
├─ core/                 canonical workflow and policies (installed to .aiek/core/)
│  ├─ WORKFLOW.md        the one workflow; stage owners; mandatory vs optional
│  ├─ classification.md  Small / Normal / Large rubric and hard triggers
│  ├─ handoffs.md        BLOCKED / NEEDS DECISION / DONE formats
│  ├─ parallelism.md     five independence rules
│  ├─ adapter-contract.md, command-discovery.md
│  └─ router.md          block inserted into the project's AGENTS.md
├─ skills/               Agent Skills (SKILL.md), harness-neutral
│  ├─ shaping-feature    discovery → Feature Brief → stop
│  ├─ executing-task     task loop over Spec Kit tasks.md (or a Small change)
│  ├─ verifying-change   mandatory evidence gate
│  ├─ reviewing-change   lane-appropriate review + receiving feedback
│  ├─ systematic-debugging, using-worktrees, parallel-development
│  └─ test-driven-development, finishing-branch   (optional)
├─ speckit/              Spec Kit extension (aiek), preset (aiek-core), workflows
├─ adapters/             default (auto-discovers commands) and _template
├─ scripts/install.sh    installs into a project
└─ docs/                 upstream mapping, adding an adapter
```

## Install into a project

Run these commands:

```bash
cd /path/to/project
specify init --here --integration claude     # once; or codex, agy, copilot, ...
/path/to/ai-engineering-kit/scripts/install.sh . --speckit
# options: --harness claude,codex,agy  --adapter <name|path>  --link  --force  --dry-run
```

This installs:

- `.aiek/core/*.md`, `.aiek/adapter.md`, and `.aiek/NOTICE.md`
- The skills into `.claude/skills/` (Claude Code) and/or `.agents/skills/` (Codex, Antigravity)
- A marked kit block in `AGENTS.md`, and a `CLAUDE.md` that imports it for Claude Code
- With `--speckit`: the `aiek` extension, the `aiek-core` preset, and the two workflows

Next steps:

- Fill in `.aiek/adapter.md` (see [docs/adding-an-adapter.md](docs/adding-an-adapter.md)).
- For "should we build this?" triage, also run `specify extension add assess`.

**Do not install Superpowers alongside this kit** in the same active session, including globally enabled plugins/skills. Its bootstrap and brainstorming → writing-plans chain duplicate the responsibilities this kit gives to Spec Kit.

### Harnesses

| Harness | Skills | Instructions | Spec Kit commands |
|---|---|---|---|
| Claude Code | `.claude/skills/` | `CLAUDE.md` → `@AGENTS.md` | `/speckit-<cmd>` |
| Codex | `.agents/skills/` | `AGENTS.md` | `$speckit-<cmd>` |
| Antigravity | `.agents/skills/` | `AGENTS.md` | `/speckit-<cmd>` |
| Others (DeepSeek-based CLIs, etc.) | copy `skills/` to the agent's skills dir, or point it at `.aiek/` | `AGENTS.md` or equivalent | per `specify init --integration` |

The installer requires Bash and Python 3 (use a compatible shell on other platforms).
Skill loading, command invocation and subagents still depend on the harness. Codex repository
skill discovery follows the [official customization docs](https://learn.chatgpt.com/docs/customization/overview#skills).

Skills use only the open Agent Skills fields (`name`, `description`). Nothing is harness-specific except the install path.

## Using it day to day

| You say | What happens |
|---|---|
| "Fix the typo in the signup email" | SMALL: execute → verify → self-review → DONE |
| "Users want to export reports somehow" | `shaping-feature` asks questions → Feature Brief → you run `specify` with it |
| "Add CSV export to the reports page" | NORMAL: specify → plan → tasks → READY TO BUILD → implement → verify/review hooks → DONE |
| "Move billing to usage-based pricing" | LARGE: research, spec, plan → NEEDS DECISION → tasks → analyze → worktree → implement → independent review → DONE |
| "Should we build offline mode?" | Spec Kit `assess` → go / needs-clarification / kill |

For supervised workflow runs (see [runner limits](speckit/README.md)):
`specify workflow run aiek-normal --input request="..."`

## Principles

- One workflow, one planner (Spec Kit), and one source of truth (`specs/<feature>/`).
- Verification before DONE is mandatory. TDD is adapter-controlled.
- Parallel only when five independence rules hold.
- Project specifics live in adapters and presets, never in skills.
- No ceremony for trivial changes.

## Validate the kit

Run `scripts/check.sh`, then `scripts/install.sh <existing-scratch-dir> --dry-run`.
Run `python scripts/test.py` in an environment with PyYAML for installer and negative checks.
With a compatible `specify` on PATH, run `python scripts/test-speckit.py` for real composition
checks across the supported integrations. These tests do not invoke coding agents.

See [the workflow audit](docs/audit-2026-10-17.md) for fixes, evidence and remaining limits.

## Credits

Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT) and built on [github/spec-kit](https://github.com/github/spec-kit) (MIT). See [NOTICE.md](NOTICE.md) and [docs/upstream-mapping.md](docs/upstream-mapping.md).
