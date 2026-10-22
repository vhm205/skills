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

- One workflow, one planner (Spec Kit), and one source of truth (`specs/<feature>/`).
- Verification before DONE is mandatory. TDD is adapter-controlled. Where behavior cannot be
  tested, observed system state and measured thresholds carry the same burden of proof.
- Parallel only when five independence rules hold.
- Project specifics live in adapters and presets, never in skills.
- No ceremony for trivial changes.

## Validate the kit

Run `scripts/check.sh`, then `scripts/install.sh <existing-scratch-dir> --dry-run`.
Run `python scripts/test.py` in an environment with PyYAML for installer and negative checks.
With a compatible `specify` on PATH, run `python scripts/test-speckit.py` for real composition
checks across the supported integrations. These tests do not invoke coding agents.

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

## Credits

Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT) and built on [github/spec-kit](https://github.com/github/spec-kit) (MIT). See [NOTICE.md](NOTICE.md) and [docs/upstream-mapping.md](docs/upstream-mapping.md).

## Local Review UI

The optional Vietnamese review UI reads the documents in an installed project. It shows
requirements, declared lane, decision sections, task checkboxes, source references and changes
since your last local review baseline. The workflow map distinguishes document availability, human review and human-reported command evidence. A docs Copilot answers questions through supported CLI adapters or a compatible API; it does not execute workflow tasks or certify gates.

The npm package is prepared for release; **it has not been published by this change**.
After publication, the intended command is:

```bash
cd /path/to/project
npx ai-engineering-kit web
# or: npx ai-engineering-kit web --project /path/to/project --port 3080 --no-open
```

Node.js 22.12 or newer is required. Port 3080 is the default; if busy, the server tries the next
port. An explicitly selected busy port fails. The server binds only `127.0.0.1`; the URL printed
by the CLI opens a local session. Keep that URL private. The fragment token is removed after
session setup. Use `Ctrl+C` to close the server and filesystem watcher.

### Run from this checkout

```bash
npm ci
npm run build
node dist/server/cli.js web
# To review another project, replace the path below with its actual absolute directory:
# node dist/server/cli.js web --project "/absolute/path/to/your/project"
```

No Python, Spec Kit CLI, API key, development server or runtime CDN is needed to **run the built
UI**. The existing installer still owns installing the kit into projects; opening the UI never
installs or upgrades project files. A project without `.aiek/` can still browse its specs, with
a visible warning. Git is optional: review diffs include uncommitted documents.

### Review and edit

1. Select a feature explicitly from `specs/` in the sidebar.
2. Inspect overview, decisions, tasks and exact source documents. Core and adapter come from
   the selected project's installed `.aiek/`, not from the UI package's bundled policies.
3. Choose **Lưu mốc đã review** to save the currently displayed document revision. Later changes
   appear under **Thay đổi**. Saving again explicitly replaces that feature's previous baseline.
4. Open a source document, expand **Chỉnh sửa section trong tài liệu này** and select a section.
   Preserve its heading, preview the diff and save. Decision sections also have an edit shortcut
   under **Cần xử lý**. Markdown sections in other feature documents are editable too.
5. If another editor changed the file, saving returns a conflict and retains your draft. Load
   the new source, compare it with the retained draft and preview again before saving.

A saved decision does not approve a workflow gate. Checked tasks and `PASS (planned)` are
statements in documents, not verified execution evidence. Results that exist only in agent
chat are not available to this UI. Source parsing is structural; arbitrary custom headings
remain readable without guessed state or dependency relationships.

### Local data and limits

Baselines are stored outside the project, separately for each canonical project/worktree path
and feature. Each feature keeps one full baseline, up to twenty compact review-round records and twenty
human command-evidence records; earlier full document versions are not retained.

- macOS: `~/Library/Application Support/ai-engineering-kit`
- Linux: `$XDG_DATA_HOME/ai-engineering-kit`, default `~/.local/share/ai-engineering-kit`
- Windows: `%LOCALAPPDATA%/ai-engineering-kit`

`AIEK_DATA_DIR` overrides that location for isolated tests. Delete the local baseline JSON files
to reset review history; project documents and Git are unaffected. Baselines contain copies of
reviewed documents, so treat the data directory with the same care as the project.

The reader rejects filesystem symlinks, including symlinked installed kit assets; use the
installer's copy mode when those sources are needed. Files must be valid UTF-8 Markdown,
limited to 2 MiB each, 20 MiB per feature and 512 documents. Source scanning supports nested
documents with bounded depth. Raw HTML and remote images are not executed/rendered.

Section saves retain unrelated bytes and file permissions, serialize this server's writes,
and recheck full-file hash and inode before same-directory atomic replacement. Uncooperative
external editors can still race the final check/rename window; the UI cannot lock other tools.
Do not use this as a shared or remote document editing service.

The watcher falls back to local polling on resource/permission limits. To force polling,
set `AIEK_WATCH_POLLING=1`. Connection/watcher warnings remain visible; manual reload always
reads documents again. No analytics or outbound model requests are made.

### Validate and prepare a release

```bash
npm run check
npx playwright install chromium
npm run test:e2e
npm run test:package
npm pack
```

`npm run test:package` launches the actual tarball through npm exec in a scratch project with
spaces in its path, checks authentication and built assets, then shuts it down. If Chrome is
already installed, `AIEK_BROWSER_CHANNEL=chrome npm run test:e2e` uses it instead of downloading
a test browser. Re-run the kit checks above when changing installer/checker behavior.

`manifest.json` is the version source; `package.json` must match or the build fails. Inspect
`npm pack --dry-run` and confirm npm package-name ownership before publishing. Registry
publication and credentials are separate from local validation; no publish step runs here.


### Review each workflow output

After a command saves docs, **Vòng review** lists new, modified and deleted documents. Review
cards, story cards and phase progress provide structure; exact Markdown and source positions
remain available. Save the displayed revision with **Lưu mốc đã review** before moving on.
The workflow shows a recommended next action based on the canonical lane and available docs.
A document's presence does not establish which command created it or that the command passed.

Large lanes include analyze and worktree checkpoints. Expand **Ghi nhận analyze / worktree /
kiểm chứng / review đã chạy** to record a command result or reviewer conclusion. These records
are explicitly human-reported and tied to the current feature revision; a later document edit
makes them stale. A baseline is a human review marker, not a gate approval. Code-only changes
are outside this docs UI and cannot invalidate these records automatically; verify against the
actual code revision before integration.

### Docs Copilot

Open **Trợ lý AI**, then **Kết nối AI**:

- **API tương thích OpenAI**: enter base URL, model ID and API key. The adapter sends Chat
  Completions (`POST <base>/chat/completions`). HTTPS is required except for loopback HTTP
  providers. Redirects are refused. API keys stay only in server memory, are never returned by
  settings endpoints or saved in project/local storage, and are forgotten at shutdown.
- **Codex CLI**: an installed `codex` with ephemeral exec, ignore-config and read-only options
  is required. The adapter ignores user/project configuration, disables shell execution and
  supplies context on stdin from an empty temporary directory. Existing CLI login is reused;
  custom provider profiles from user config are not loaded.
- **Claude CLI**: requires print, safe mode, tool restrictions, strict MCP and no-session
  persistence options. Uses no tools or customizations and an empty MCP configuration. It
  uses existing CLI authentication from an empty temporary directory.
- **agy / other agents**: **Prompt cho agy / agent khác** creates a copyable context-and-question
  prompt. Direct agy execution is deferred until a fully restricted adapter is verified.

These are fresh questions, not attachments to running terminal conversations. Missing binaries
or unsupported CLI versions are shown in settings. CLI availability does not prove provider
login or quota; those are checked only when sending a question.

Preview **Tài liệu sẽ gửi** and optionally select feature documents. Project overview includes
spec, plan and tasks from at most twenty features in sorted order. Document text is bounded to
96000 characters total, 24000 per feature document, and reports truncation. Only feature Markdown
and installed workflow/handoff context are read; code, environment files and chat transcripts
are not included. Sending shares the displayed context with the configured provider or CLI.
No model call occurs while configuring or previewing. The provider may retain data according
to its policy. Never put credentials into project documents or questions.

Responses identify their source manifest and docs revision. A changed context is labeled stale;
refresh context after other features change in project scope. Requests whose preview is stale
are rejected before sending. **Hủy câu hỏi** cancels network/CLI work and retains the question.
One AI request runs per local server, with a two-minute timeout and bounded output. Chat history
is transient in the mounted view and is not saved to disk. Copilot has no project-write or
workflow-run action. Its output remains advice to review against the source.

Provider interfaces were checked against installed CLI help and official documentation:
[OpenAI Chat Completions](https://developers.openai.com/api/reference/chat-completions/overview),
[Claude headless mode](https://code.claude.com/docs/en/headless) and
[agy headless mode](https://www.antigravity.google/docs/cli/headless/).
