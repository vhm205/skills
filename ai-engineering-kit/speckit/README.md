# Spec Kit layer

Spec Kit owns requirements, plans and tasks. This folder contains only small, standard Spec Kit
components that connect those artifacts to the kit's execution skills. Nothing here forks
Spec Kit.

| Component | Path | What it does |
|---|---|---|
| Extension `aiek` | `extensions/aiek/` | Commands `route`, `ready`, `verify`, `review`. Hooks: `after_tasks` → READY TO BUILD gate; `after_implement` → verify, then review + DONE (all mandatory) |
| Preset `aiek-core` | `presets/aiek-core/` | Wraps `specify` (Feature Brief intake), `plan` (decision gate), `tasks` (strict `[P]`, `Verify:` lines), `implement` (kit execution discipline) |
| Workflow `aiek-normal` | `workflows/aiek-normal/` | specify → clarify → plan → tasks → implement, no human gates |
| Workflow `aiek-large` | `workflows/aiek-large/` | specify → clarify → plan → **decision gate** → tasks → analyze → **ready gate** → implement |

Requires Spec Kit ≥ 1.0 (preset composition and workflows). Tested against 1.2.2.dev0.

## Install

`scripts/install.sh <project> --speckit` does this. By hand, from the project root:

```bash
specify extension add --dev /path/to/ai-engineering-kit/speckit/extensions/aiek
specify preset add   --dev /path/to/ai-engineering-kit/speckit/presets/aiek-core --priority 10
specify workflow add --dev /path/to/ai-engineering-kit/speckit/workflows/aiek-normal
specify workflow add --dev /path/to/ai-engineering-kit/speckit/workflows/aiek-large
# optional, for "should we build this?":
specify extension add assess
```

## Use

Interactive (any agent): run the Spec Kit commands as usual (`/speckit-specify`, `$speckit-plan`, …
depending on the agent). The preset and hooks apply automatically.

Workflow runner (supervised):

Hooks and textual BLOCKED/NEEDS DECISION responses are agent instructions, not process-level
stop signals. A successful agent exit does not prove that the requested stage succeeded.
The implementation wrapper rechecks readiness, but unattended safety is not guaranteed.
Inspect each stage outcome; do not treat this runner as an autonomous approval system.
The Large workflow deliberately adds two explicit human gates, even when no decision remains;
use interactive commands for the canonical conditional checkpoint path.

```bash
specify workflow run aiek-normal --input request="docs/briefs/2026-10-17-export.md"
specify workflow run aiek-large  --input request="Move billing to usage-based pricing"
specify workflow resume <run_id>       # after approving a gate
```

## Why there is no bundle

Spec Kit bundles pin components that must come from a catalog. A local bundle supplies only
the manifest, not its payloads. Until the kit's extension and workflows are published to a
catalog, a bundle would not install. Registering with `--dev` does the same job. Revisit once
the components are published.

## Dependencies on the rest of the kit

The commands reference `.aiek/core/*.md`, `.aiek/adapter.md`, and the kit skills
(`verifying-change`, `reviewing-change`, `executing-task`, …). Install the whole kit with
`scripts/install.sh`, not this folder alone.
