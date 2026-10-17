# Command Discovery

Used when an adapter key is `auto` or missing (`.aiek/adapter.md`).

Look in this order and use the first match. Say in one line which command you picked and why.

1. Project docs: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md` ("how to test", "development").
2. Task runners: `Makefile` / `justfile` / `Taskfile.yml` targets named `test`, `lint`, `typecheck`, `check`, `build`, `setup`/`install`, `dev`/`run`.
3. Ecosystem manifests:
   - `package.json` scripts (package manager from the lockfile: `pnpm-lock.yaml` → pnpm,
     `yarn.lock` → yarn, `bun.lockb` → bun, else npm)
   - `pyproject.toml` / `uv.lock` / `poetry.lock` (`uv run pytest`, `ruff check`, `mypy`/`pyright` if configured)
   - `Cargo.toml` (`cargo test`, `cargo clippy`, `cargo build`)
   - `go.mod` (`go test ./...`, `go vet ./...`, `go build ./...`)
   - other: the ecosystem's standard commands, only if the config for them exists
4. CI config (`.github/workflows/*.yml`, `.gitlab-ci.yml`): the commands CI runs are the
   commands that matter.

If nothing is found for a check, it is **not available**. Do not invent one; list it under
"Remaining risks" in DONE.
