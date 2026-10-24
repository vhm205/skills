# AI Engineering Kit

A single, project-agnostic workflow for small teams using coding agents (Claude Code, Codex, Antigravity, DeepSeek-based agents, …).

- **Discovery** (`exploring-idea`, `shaping-feature`, `intaking-ticket`): Decides whether to
  build it, shapes how it should work, or turns a tracker's acceptance criteria into criteria
  somebody can actually check — then stops.
- **New project** (`shaping-project` + Spec Kit roadmap): Turns a BRD into an approved MVP roadmap, then runs the first slice through an existing lane.
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
├─ KIT.md                repository overview for humans (not installed as a skill)
├─ core/                 canonical workflow and policies (installed to .aiek/core/)
│  ├─ WORKFLOW.md        the one workflow; stage owners; mandatory vs optional
│  ├─ classification.md  Small / Normal / Large rubric and hard triggers
│  ├─ handoffs.md        BLOCKED / NEEDS DECISION / DONE formats
│  ├─ parallelism.md     five independence rules
│  ├─ adapter-contract.md, command-discovery.md
│  └─ router.md          block inserted into the project's AGENTS.md
├─ skills/               Agent Skills (SKILL.md), harness-neutral
│  ├─ exploring-idea     should we build it? → Idea Note → drop / shape / assess / decide
│  ├─ shaping-feature    discovery → Feature Brief → stop
│  ├─ intaking-ticket    criteria from a tracker → checkable criteria + traceability → stop
│  ├─ shaping-project    BRD discovery → Project Brief → stop
│  ├─ executing-task     task loop over Spec Kit tasks.md (or a Small change)
│  ├─ shipping-infrastructure  infra/pipeline/deploy/capacity: ops evidence, not tests
│  ├─ verifying-change   mandatory evidence gate
│  ├─ reviewing-change   lane-appropriate review + receiving feedback
│  ├─ authoring-pr       PR description from evidence + author self-review
│  ├─ accepting-change   acceptance pass: scenario re-run, sign-off sheet, ops evidence
│  ├─ systematic-debugging, using-worktrees, parallel-development
│  └─ test-driven-development, finishing-branch   (optional)
├─ speckit/              Spec Kit extension (aiek), preset (aiek-core), workflows
├─ adapters/             default (auto-discovers commands), orchexa, and _template
├─ scripts/install.sh    installs into an existing project
├─ scripts/init-project.sh  creates an empty project from a BRD
└─ docs/                 local review UI, workflow guide, adapter guide, plans
```

The root [`KIT.md`](KIT.md) is a repository overview for humans, not a skill: the installer
copies the individual skills from `skills/`. Earlier versions shipped a root `SKILL.md`, which
was ambiguous because a kit whose unit of installation is the individual skill could also be
loaded as if it were one meta-skill. `KIT.md` has no frontmatter and is never installed.

## Install into a project

From npm (no checkout, no bash required):

```bash
cd /path/to/project
specify init --here --integration claude     # once; or codex, agy, copilot, ...
npx @moment/aiek install . --speckit
# options: --harness claude,codex,agy  --adapter <name|path>  --profile core|discovery|full
#          --only <skills>  --skip <skills>  --prefix <p|none>
#          --link  --force  --dry-run
```

From a checkout (kit development, CI):

```bash
/path/to/ai-engineering-kit/scripts/install.sh . --speckit
```

Both installers produce the same tree; `tests/install.test.ts` asserts it byte for byte. The
Node CLI has no bash dependency, so it also works on Windows.

This installs:

- `.aiek/core/*.md`, `.aiek/adapter.md`, and `.aiek/NOTICE.md`
- The skills into `.claude/skills/` (Claude Code) and/or `.agents/skills/` (Codex, Antigravity)
- `.aiek/scripts/*.py`: optional helper scripts (`resolve_adapter`, `verify`, `worktree`,
  `traceability`) that skills use when present and that never replace the manual fallback
- A marked kit block in `AGENTS.md`, and a `CLAUDE.md` that imports it for Claude Code
- With `--speckit`: the `aiek` extension, the `aiek-core` preset, and the two workflows

The default `--profile full` installs all 15 skills. Use `--profile core` for the 11
execution/verification/integration skills, or `--profile discovery` for the 4 discovery skills;
`--only` and `--skip` tune the selection. Adapter `references/` and `scripts/` are copied to
`.aiek/adapter/` when the adapter has them.

Skills are installed under the `aiek-` namespace by default (`aiek-executing-task`,
`aiek-verifying-change`, …), so a project or another kit can keep a bare `executing-task` without
the two colliding. The prefix is applied to the skill directory, the `SKILL.md` `name`, the
router text in `AGENTS.md` and every skill reference inside the installed copies. Pass
`--prefix none` for the bare names, or `--prefix <ns>` for a different namespace. Skills
installed before this default existed keep their bare names; delete those directories after
installing with a prefix. `--prefix` cannot be combined with `--link`.

Next steps:

- Fill in `.aiek/adapter.md` (see [docs/adding-an-adapter.md](docs/adding-an-adapter.md)).
- For "should we build this?" triage, also run `specify extension add assess`.

**Skill dependencies.** Skill frontmatter contains only the open Agent Skills fields `name` and
`description` — no extra dependency fields. Instead, the installed skills depend on the files the
installer writes: `.aiek/core/*.md` (the canonical workflow and policies) and `.aiek/adapter.md`
(this project's commands, paths, risk areas and conventions). Both are resolved at the installed
paths, not from the kit checkout. If `.aiek/` is missing, the skills have no rules or project
facts to follow: re-run `scripts/install.sh` for the project instead of working around it.

**Agent Skills ecosystem.** The tarball ships `skills/<name>/SKILL.md` at its root, so
`npm i -D @moment/aiek && npx skills experimental_sync` also discovers the skills for
[`npx skills`](https://github.com/vercel-labs/skills) users. That path installs bare names and
does not write `.aiek/`; use `npx @moment/aiek install` when you want the workflow files,
profiles, adapter and `aiek-` namespace.

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

`.agents/skills/` is the canonical installed skills root; `.claude/skills/` is an optional
mirror for Claude Code. Install both only when both harnesses are used: the checker verifies the
two trees stay in parity. Skills use only the open Agent Skills fields (`name`, `description`);
nothing is harness-specific except the install path.

## Guide

A narrative walkthrough of all 15 skills — what each is for, when to reach for it, where it
stops, and five end-to-end scenarios — is in
[docs/huong-dan-workflow.md](docs/huong-dan-workflow.md) (Vietnamese).

## Using it day to day

| You say | What happens |
|---|---|
| "Fix the typo in the signup email" | SMALL: execute → verify → self-review → DONE |
| "Users want to export reports somehow" | `shaping-feature` asks questions → Feature Brief → you run `specify` with it |
| "Add CSV export to the reports page" | NORMAL: specify → plan → tasks → READY TO BUILD → implement → verify/review hooks → DONE |
| "Move billing to usage-based pricing" | LARGE: research, spec, plan → NEEDS DECISION → tasks → analyze → worktree → implement → independent review → DONE |
| "Should we build offline mode?" | `exploring-idea` → Idea Note → drop, shape, or Spec Kit `assess` |
| "Here is ticket ABC-123 with its acceptance criteria" | `intaking-ticket` → checkable criteria + traceability, or BLOCKED with questions for the requester |
| "Move staging onto the new cluster" | INFRA: decision recorded → `shipping-infrastructure` → ops evidence → rehearsed rollback → `accepting-change` |
| "Open the PR for this" | `authoring-pr` → description built from the verification evidence, author self-review first |
| "Is this ready to release?" | `accepting-change` → scenario re-run + acceptance sheet + sign-off |

For supervised workflow runs (see [runner limits](speckit/README.md)):
`specify workflow run aiek-normal --input request="..."`

## Principles

- One workflow, one planner (Spec Kit, or the external planner named by `planning.mode`), and one
  source of truth for each artifact. One fact, one owner: link, never copy
  (`core/documentation.md`).
- Verification before DONE is mandatory. TDD is adapter-controlled. Where behavior cannot be
  tested, observed system state and measured thresholds carry the same burden of proof.
- Parallel only when five independence rules hold.
- Project specifics live in adapters and presets, never in skills.
- No ceremony for trivial changes.

## Validate the kit

Run `scripts/check.sh` (static contracts, skill metadata and `.claude`/`.agents` parity), then
`scripts/install.sh <existing-scratch-dir> --dry-run`. Run `python scripts/test.py` in an
environment with PyYAML for installer, profile and negative checks, and `python scripts/test_scripts.py`
for the helper scripts (standard library only). With a compatible `specify` on PATH, run
`python scripts/test-speckit.py` for real composition checks across the supported integrations.
These tests do not invoke coding agents.

The eval harness is harness-agnostic: `python3 scripts/eval_trigger.py --mock` and
`python3 scripts/eval_tasks.py --mock` run deterministic trigger/behavior checks offline
(the primary real harness is DeepSeek Harness, with Claude Code and Codex as optional smoke
harnesses). Results and limitations — including the per-scenario behaviour evidence and the preserved raw one-pass — are in
[docs/eval-2026-10-23.md](docs/eval-2026-10-23.md).

See [the workflow audit](docs/audit-2026-10-17.md) for fixes, evidence and remaining limits.

## Start a new project from a BRD

```bash
/path/to/ai-engineering-kit/scripts/init-project.sh /path/to/new-project \
  --brd /path/to/requirements.md --integration codex
cd /path/to/new-project
specify workflow run aiek-project --input brd="docs/inputs/requirements.md"
```

Use `claude`, `codex`, or `agy` for `--integration`. The target must be absent or empty; the
bootstrap refuses existing content and never overwrites it. It copies the BRD into
`docs/inputs/`, initializes Spec Kit and installs this kit. Check the copied BRD for sensitive
material before committing it. The default adapter discovers build commands once code exists;
fill in `.aiek/adapter.md` as the project takes shape.

The project workflow creates `docs/briefs/project-brief.md`, runs Spec Kit constitution,
creates `ROADMAP.md`, and pauses for explicit approval of the MVP. All project phases have
outcome goals; only MVP phases have detailed, independently testable slices. The first
approved slice enters the existing Small/Normal/Large path and the workflow stops after it.
Each later slice gets its own Spec Kit spec, plan, and tasks. Run the lane for later slices
one at a time after reconciling the roadmap.

The `aiek-project` runner is supervised. Its gate pauses for approval, but agent command
responses are not machine-enforced stage success. Inspect the Brief, constitution, roadmap,
first spec and DONE evidence rather than treating a successful runner exit as proof.

## Local Review UI

The optional Vietnamese review UI reads the documents in an installed project: requirements,
declared lane, decision sections, task checkboxes, source references, changes since your last
local review baseline, and a docs Copilot. It does not execute workflow tasks or certify gates.
The npm package is prepared for release but **has not been published by this change**; after
publication the intended command is `npx ai-engineering-kit web`.

Full setup, review flow, local data limits and the Copilot guide:
[docs/local-review-ui.md](docs/local-review-ui.md).

## Credits

Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT) and built on [github/spec-kit](https://github.com/github/spec-kit) (MIT). See [NOTICE.md](NOTICE.md) and [docs/upstream-mapping.md](docs/upstream-mapping.md).
