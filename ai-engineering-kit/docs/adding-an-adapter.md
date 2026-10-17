# Adding a Project Adapter (e.g. Plane, Orchexa)

An adapter teaches the kit one project's facts: commands, risky areas, review rules, tracker.
It never changes the workflow. Contract: [`core/adapter-contract.md`](../core/adapter-contract.md).

## 1. Create it

```bash
cp -R adapters/_template adapters/plane
```

Or keep the adapter **in the project repo** (recommended once it stabilizes) and pass its path
to the installer. The kit then stays free of project details.

## 2. Fill in `adapter.md`

Work from the project's real sources (CI config, Makefile, package.json, CONTRIBUTING):

```yaml
---
adapter: plane
default_branch: preview
verify:
  setup: pnpm install
  test: pnpm turbo run test
  lint: pnpm turbo run check:lint
  typecheck: pnpm turbo run check:types
  build: pnpm turbo run build
  run: pnpm dev
tdd: optional
risk_areas: ["apps/api/plane/db/migrations/**", "apps/api/plane/authentication/**"]
review:
  human_required_for: ["apps/api/plane/authentication/**"]
tracker: plane
tracker_notes: "Reference the work item ID in the branch name and PR title."
---
```

_(Commands above are illustrative; verify each one against the project before relying on it.)_

Then add short prose: architecture boundaries, conventions, "never" rules, how to run locally,
glossary. Link to existing docs instead of copying them.

## 3. Optional: Spec Kit customization

If the project needs extra spec sections (e.g. Orchexa: tenant isolation and agent-pipeline
impact on every spec), edit `adapters/<name>/speckit-preset/`. It is installed with priority 5,
ahead of the kit preset (10). Durable engineering *principles* belong in the project's
`.specify/memory/constitution.md` (run Spec Kit `constitution`), not in the adapter.

## 4. Install into the project

```bash
cd /path/to/project
specify init --here --integration claude        # or codex, agy, ... (once per project)
/path/to/ai-engineering-kit/scripts/install.sh . --adapter plane --speckit
# adapter kept in the project repo instead:
/path/to/ai-engineering-kit/scripts/install.sh . --adapter ./tools/aiek-adapter --speckit
```

## 5. Check it

- `.aiek/adapter.md` is the project's adapter
- Ask the agent: "Classify this change: <real example>". It should name the lane and cite the adapter's risk areas.
- Ask for a Small change and confirm DONE quotes the adapter's commands with real output.

## Rules of thumb

- An adapter can raise rigor (risk areas, required TDD, human review), never lower it.
- No secrets; refer to env var names.
- Keep the prose under ~150 lines. If it grows, link out.
- Re-running `install.sh` never overwrites `.aiek/adapter.md` unless you pass `--force`.
