# Agent Instructions (kit development)

This repository *is* the AI Engineering Kit. These rules apply when changing the kit itself.
Projects that install the kit get `core/router.md` instead.

## Boundaries

- `core/` is the single canonical workflow. Do not restate its rules inside skills. Link to
  `.aiek/core/<file>.md` (the installed path) instead.
- `skills/` must stay project-agnostic: no language, framework, tracker or company names.
  Project facts come from `.aiek/adapter.md`.
- Spec Kit owns planning. No skill may create plans, task lists or spec documents.
  `shaping-feature` ends at a Feature Brief.
- `speckit/` contains only standard Spec Kit components (extension, preset, workflows). Wrap
  core commands; never replace or fork them.
- Adapters configure; they never change stages or handoff formats.

## Skill format

- `skills/<name>/SKILL.md` with frontmatter `name` (= directory name, lowercase-hyphenated) and
  `description` (third person, says *when* to use it, ≤ 1024 chars). No other fields.
- Keep SKILL.md short (aim < 120 lines). Move templates and long guidance to `references/`.
- Adapted content keeps its attribution footer; update `NOTICE.md` when adding adaptations.

## Before claiming a change works

```bash
scripts/check.sh            # frontmatter, links, YAML manifests
scripts/install.sh /tmp/x --dry-run
```

For installer or checker changes, also run `python scripts/test.py` in an environment with
PyYAML. For reproducible integration checks, `python scripts/test-speckit.py` uses `specify`
on PATH and tests the three supported integrations without invoking coding agents.

For Spec Kit changes, install into a scratch project (`specify init`, then
`install.sh --speckit`) and confirm the rendered commands contain the kit sections.
