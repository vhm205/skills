# Adapter Contract

The kit's core and skills are project-agnostic. Everything that differs between projects —
commands, conventions, risk areas, tracker, review rules — lives in an **adapter**.

In a project that installed the kit, the active adapter is a single file:
`.aiek/adapter.md`. Skills read it; they never hard-code project facts.

## Layout of an adapter in this kit

```text
adapters/<name>/
├─ adapter.md              # required: YAML frontmatter (machine-readable) + prose conventions
├─ speckit-preset/         # optional: a Spec Kit preset with project-specific overrides
│  ├─ preset.yml           #   e.g. constitution-template, spec-template additions
│  └─ ...
└─ README.md               # optional: what this adapter is for
```

## `adapter.md` frontmatter

All keys are optional. A missing key, or the value `auto`, is resolved with
[command-discovery.md](command-discovery.md). There is no adapter inheritance in v0: the
agent reads one file, so put every non-default value in it.

```yaml
---
adapter: my-project          # name
default_branch: main         # or "auto" (detect from origin/HEAD)

verify:                      # used by verifying-change, using-worktrees, executing-task
  setup: pnpm install        # dependency/bootstrap step for a fresh worktree
  test: pnpm test
  test_targeted: pnpm test -- {path}   # optional; {path} is replaced
  lint: pnpm lint
  typecheck: pnpm typecheck
  build: pnpm build
  e2e: null                  # null = not available; say so in DONE
  uat: null                  # full scenario/acceptance suite, for accepting-change
  deploy_check: null         # proves a deployed environment is in the intended state
  run: pnpm dev              # how to observe the app, for UI verification

baseline: null               # where known-accepted failures are listed; see below
output_language: null        # language for PR bodies, reports and acceptance sheets
pr_template: null            # path to the project's PR template; null = kit default sections
pr_required_sections: []     # section titles authoring-pr must not leave out

tdd: optional                # optional | required
tdd_required_paths: []       # globs where TDD is required even if tdd: optional

worktree_dir: .worktrees
branch_pattern: "{feature}"  # {feature} = Spec Kit feature dir name, {slug}, {type}
commit_policy: per-task      # per-task | per-change | manual
integration: ask             # ask | pr | merge (finishing-branch default; "ask" recommended)

brief_dir: docs/briefs       # where shaping-feature saves briefs when asked to persist

risk_areas:                  # touching any of these forces the LARGE lane
  - "src/auth/**"
  - "migrations/**"
review:
  human_required_for: []     # globs/areas that always need a human reviewer

tracker: none                # none | github | plane | jira | linear | ...
tracker_notes: ""            # how tasks map to tickets, if at all
---
```

## `baseline`

A project with known, accepted failures sets `baseline` to where that list lives. "Green" then
means *no failures beyond the baseline*, not zero failures, for `verifying-change` and
`test-driven-development`. Say whether the list is machine-readable (a file a script compares
against) or prose a person must read, because the two cost very different amounts of attention.
A baseline may shrink. It may never be widened to absorb a new failure.

## Prose section

Below the frontmatter, write short, imperative project rules the skills should respect:
code style, architecture boundaries, naming, "never do X" rules, how to run things locally,
domain glossary. Keep it under ~150 lines. Link to longer project docs instead of copying them.

## Rules for adapters

1. **No workflow changes.** Adapters configure the canonical workflow; they do not add
   stages, rename handoffs, or introduce a second planning artifact.
2. **Risk can only go up.** An adapter may add `risk_areas` or require TDD or human review;
   it may not exempt changes from verification.
3. **Routing is allowed; redefining stages is not.** An adapter may say "symptom X is already
   covered by the project's own playbook Y" and send the agent there. It may not add a stage,
   rename a handoff, or introduce a second planning artifact.
4. **Spec Kit customization goes through a preset.** Project-specific spec/plan/tasks
   template changes or a constitution template belong in `speckit-preset/`, installed with a
   lower priority number (= higher precedence) than the kit preset.
5. **Secrets never go in an adapter.** Reference env var names, not values.

## Spec Kit constitution vs. adapter

- `.specify/memory/constitution.md`: durable engineering *principles* the spec/plan must
  satisfy (e.g. "library-first", "every API change is versioned"). Owned by Spec Kit.
- `.aiek/adapter.md`: operational *facts and commands* (how to test, where risky code lives).

If a rule is a principle the plan must be checked against, put it in the constitution.
If it is a command or a path, put it in the adapter.
