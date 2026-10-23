# AI Engineering Kit — repository overview

This repository **is** the AI Engineering Kit. It is not itself an installable Agent Skill: the
installer copies the 15 individual skills from `skills/` into a target project.

## What it is

A project-agnostic engineering workflow for small teams using coding agents (Claude Code, Codex,
Antigravity, DeepSeek-based agents, …). It combines Spec Kit planning discipline
(requirements → plan → tasks) with disciplined execution skills: discovery that stops before
code, mandatory verification, lane-appropriate review, and three human handoffs
(BLOCKED / NEEDS DECISION / DONE).

Start with [README.md](README.md) for the workflow, install steps, harness support and validation
commands. The narrative walkthrough of every skill is
[docs/huong-dan-workflow.md](docs/huong-dan-workflow.md) (Vietnamese).

## Repository layout

| Path | Contents |
|---|---|
| `README.md` | Overview, layout, install, harness matrix, day-to-day usage, validation |
| `core/` | Canonical workflow and policies; installed into the project as `.aiek/core/` |
| `skills/` | The 15 Agent Skills (`skills/<name>/SKILL.md`); installed into `.claude/skills/` or `.agents/skills/` |
| `speckit/` | Spec Kit extension (`aiek`), preset (`aiek-core`), workflows |
| `adapters/` | `default` (auto-discovers commands), `orchexa`, and `_template` |
| `scripts/` | Installer, project bootstrap, checkers, tests and helper scripts |
| `docs/` | Workflow guide, adapter guide, review UI guide, upstream mapping, plans, eval reports |
| `evals/` | Trigger and behavior eval fixtures, runner output and reports |
| `manifest.json` | Version source and skill/extension inventory |

## Install into a project

```bash
cd /path/to/project
specify init --here --integration claude     # once; or codex, agy, copilot, ...
/path/to/ai-engineering-kit/scripts/install.sh . --speckit
```

See [README.md](README.md#install-into-a-project) for options (harness, adapter, link, profile,
dry-run), what gets installed, and the harness table.

## Why KIT.md instead of a root SKILL.md

Earlier versions shipped a root `SKILL.md`. That was ambiguous: a `SKILL.md` is an installable
unit in the Agent Skills format, but this kit installs many skills, and the installer copies
each `skills/<name>/` directory individually. A root meta-skill could be loaded alongside — or
instead of — the real skills. `KIT.md` is a repository overview for humans only: it has no
frontmatter, is not installed or discovered by agents, and does not duplicate the workflow.

The canonical workflow lives in `core/`; the installable skills live in `skills/`. The optional
local review UI is documented in [docs/local-review-ui.md](docs/local-review-ui.md).
