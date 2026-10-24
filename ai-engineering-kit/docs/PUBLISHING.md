# Publishing the npm package

The kit ships as `@moment/aiek` (public). The unscoped `ai-engineering-kit` name on npm belongs
to another project, so it is not available. `manifest.json` and `package.json` must carry the
same version (`scripts/version-check.mjs` enforces it during `prepack`).

## Prerequisites

- Node 22.12+ and npm 10+.
- An npm account that owns the `@moment` scope, logged in with `npm login`
  (`npm whoami` must print your username).
- A clean working tree and passing checks.

## Release checklist

```bash
cd ai-engineering-kit
npm run check                 # typecheck + lint + vitest + build
npm run test:package          # packs the tarball, installs and launches from it
scripts/check.sh              # skill frontmatter, references, manifests
python3 scripts/test.py       # bash installer regression suite
npm pack --dry-run            # inspect the file list (81 files, ~250 kB)
npm publish --dry-run        # metadata + access check, no upload
npm publish                  # publishes with tag latest and public access
```

After publishing:

```bash
npx @moment/aiek@0.3.0 install /tmp/aiek-smoke --harness codex --profile discovery
npx @moment/aiek --version
```

## Versioning

- Patch: documentation, wording, reference fixes.
- Minor: new skills, new installer flags, adapter changes. Bump `package.json` **and**
  `manifest.json`, then add a `CHANGELOG.md` entry.
- Do not publish from a dirty tree: `dist/` is built by `prepack`, but the tarball also contains
  `skills/`, `core/`, `speckit/`, `adapters/` and the helper scripts, which come straight from the
  working tree.

## What ships

`files` in `package.json` is authoritative. It must include `dist/`, `core/`, `skills/`,
`speckit/`, `adapters/`, `manifest.json`, `KIT.md`, `NOTICE.md`, `LICENSE`, `scripts/install.sh`,
`scripts/init-project.sh` and every helper script the installer copies
(`resolve_adapter.py`, `verify.py`, `worktree.py`, `traceability.py`, `_adapter_yaml.py`).
`scripts/test-package.mjs` fails when a helper script is missing from the tarball.

## Mistakes and rollback

- Wrong version uploaded: `npm unpublish @moment/aiek@<version>` (allowed for 72 hours, and the
  version number stays burned), then publish a patch.
- Wrong content: publish a patch with the fix; do not reuse a version.
- Never publish with `--access restricted` for this package: projects install it anonymously.

## Agent Skills ecosystem

The tarball keeps `skills/<name>/SKILL.md` at its root, so `npx skills experimental_sync` also
discovers the skills from an installed dependency. That path links bare names and skips `.aiek/`;
`npx @moment/aiek install` is the supported path for the full workflow.
