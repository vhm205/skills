# Execution evidence

Implemented the approved v1: Vietnamese local review UI, structural Markdown sources, task grouping, external snapshots and guarded decision-section edits; no agent execution or npm publication.

## Checks run

| Check | Command / method | Result |
| --- | --- | --- |
| Runtime checks | `npm run check` | Typecheck, lint, 22 unit/integration tests and production build pass |
| Browser | `AIEK_BROWSER_CHANNEL=chrome npm run test:e2e` | 4 tests pass: baseline/live diff, section write, shifted-source conflict draft recovery, source refresh/deletion, script rejection and 320/768/1024/1440 layout |
| Package | `npm run test:package` | Real npm tarball through npm exec/npx: prebuilt JS/CSS, authenticated project read, unchanged scratch project and shutdown pass; exit 0 |
| Kit checker | `scripts/check.sh` | 9 skills; YAML, references, inventories and wrappers consistent |
| Installer | `scripts/install.sh /private/tmp/aiek-speckit-reference --dry-run` | Exit 0, no target changes |
| Existing Python tests | Python 3 with PyYAML, `scripts/test.py` | 8 tests pass, including generated-tree pruning and existing negative checks |
| Spec Kit integration | `scripts/test-speckit.py` | Environment incompatible: installed specify rejects existing `--non-interactive` flag; no Spec Kit components changed |

## Independent review

Fresh reviewer inspected the full change and found four Important issues: shifted section offset conflict ordering, stale open source dialog, unclosed Markdown swallowing other sections, and file mode masked by umask. All fixed with regression coverage. Reviewer scoped re-review confirms all addressed, no new blocking findings; independently reran project tests, 8/8 pass.

## Rulings

- Use approved temporary Git worktree because harness-managed checkout is outside writable roots; transfer only task-owned files back after review.
- Keep planning artifacts from upstream offline Spec Kit scaffolding instead of initializing the kit as an installed target project.
- Native watcher resource limits trigger polling fallback, surfaced in UI. This avoids losing live updates on hosts with many active watchers.
- Browser checks use installed Chrome; downloaded Playwright Chromium is optional.

## Remaining limits

No npm registry publication; Node 22.22.3 exercised, Node 24 unavailable locally. The one-minute human comprehension target is not measured. Uncooperative external writers can race the final validation/rename window; documented. No filesystem ACL/ownership preservation claim beyond ordinary permission bits. Raw documents are interpreted structurally, never as proof of executed gates.
