# Agent Instructions (kit development)

This repository *is* the AI Engineering Kit. These rules apply when changing the kit itself.
Projects that install the kit get `core/router.md` instead.

## Boundaries

- `core/` is the single canonical workflow. Do not restate its rules inside skills. Link to
  `.aiek/core/<file>.md` (the installed path) instead.
- `skills/` must stay project-agnostic: no language, framework, tracker or company names.
  Project facts come from `.aiek/adapter.md`.
- Spec Kit owns planning (or the external planner named by `planning.mode`). No skill may
  create plans, task lists or spec documents. `shaping-feature` ends at a Feature Brief.
- `speckit/` contains only standard Spec Kit components (extension, preset, workflows). Wrap
  core commands; never replace or fork them.
- Adapters configure; they never change stages or handoff formats.
- One fact, one owner; link, never copy. See `core/documentation.md`.

## Skill format

- `skills/<name>/SKILL.md` with frontmatter `name` (= directory name, lowercase-hyphenated) and
  `description` (third person, says *when* to use it, includes `Use when` triggers and a
  `Not for` exclusion, ≤ 1024 chars). No other fields.
- Keep SKILL.md at most 120 lines (hard limit 250). Move templates and long guidance to
  `references/`.
- Adapted content keeps its attribution footer; update `NOTICE.md` when adding adaptations.
- The repository root has `KIT.md` (human overview), not a `SKILL.md`: the installer copies
  individual skills, so a root skill entry would be ambiguous.

## Installed layout

- `scripts/install.sh` copies `core/`, the selected skills (profile), the adapter, and the
  helper scripts to `.aiek/scripts/`.
- `.aiek/adapter.md` is project-owned: reinstall never overwrites it without `--force`.
- `.agents/skills/` is the canonical installed skills root (D4). `.claude/skills/` is an
  optional mirror and must stay in parity.

## Before claiming a change works

```bash
scripts/check.sh            # frontmatter, links, YAML manifests, skills metadata/parity
scripts/check_skills.py . --kit . --require-trigger
scripts/install.sh /tmp/x --dry-run
```

For installer or checker changes, also run `python scripts/test.py` in an environment with
PyYAML, `python scripts/test_scripts.py` for the helper scripts, and `python3 scripts/eval_trigger.py --mock`
plus `python3 scripts/eval_tasks.py --mock` for the eval harness. For reproducible integration
checks, `python scripts/test-speckit.py` uses `specify` on PATH and tests the three supported
integrations without invoking coding agents.

For Spec Kit changes, install into a scratch project (`specify init`, then
`install.sh --speckit`) and confirm the rendered commands contain the kit sections, including
the adapter preset templates when present.

Evals: `dsh headless` is the primary real harness (DeepSeek Harness), with Claude Code and
Codex as optional smoke harnesses; CI uses the deterministic `--mock` mode and the static
checkers. Never put a passing number in docs that the harness run did not produce.
