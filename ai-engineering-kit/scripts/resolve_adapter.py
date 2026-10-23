#!/usr/bin/env python3
"""Resolve an AI Engineering Kit adapter into concrete, concrete commands.

Reads the YAML frontmatter of ``.aiek/adapter.md`` (or ``--adapter PATH``) and replaces
missing or ``auto`` command values using the discovery order from
``core/command-discovery.md``:

1. project docs (``AGENTS.md``, ``CLAUDE.md``, ``CONTRIBUTING.md``, ``README.md``),
2. task runners (``Makefile``, ``justfile``, ``Taskfile.yml``),
3. ecosystem manifests (``package.json`` + lockfile, ``pyproject.toml``/``uv.lock``/
   ``poetry.lock``, ``Cargo.toml``, ``go.mod``),
4. CI configuration (``.github/workflows/*.yml``, ``.gitlab-ci.yml``).

The script is **read-only**: it never executes project commands and never writes files.
Every resolved value carries its ``source`` (``adapter``, ``discovered``, ``derived`` or
``unavailable``) and, where relevant, the ``evidence`` the discovery used.

Exit codes: 0 = resolved, 1 = adapter/repo error, 2 = bad usage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _adapter_yaml import FrontmatterError, load_adapter  # noqa: E402

MISSING = object()

#: Every ``verify.*`` key recognised by adapter contract v2.
COMMAND_KEYS = (
    "setup",
    "test",
    "test_fast",
    "test_full",
    "test_targeted",
    "lint",
    "typecheck",
    "build",
    "e2e",
    "uat",
    "deploy_check",
    "run",
    "run_fe",
    "ui",
    "fe_test",
    "fe_lint",
    "fe_typecheck",
    "fe_build",
)

#: Keys that command discovery can fill. The rest are project facts (a URL, a command the
#: project must name explicitly) and discovery never invents them.
DISCOVERABLE_KEYS = (
    "setup",
    "test",
    "test_fast",
    "test_full",
    "test_targeted",
    "lint",
    "typecheck",
    "build",
    "e2e",
    "uat",
    "run",
)

DISCOVERY_WORDS = {
    "setup": ("install", "setup", "bootstrap", "dependencies", "deps"),
    "test": ("test",),
    "test_fast": ("test", "fast", "unit", "quick", "watch"),
    "test_full": ("test", "full", "all", "integration", "ci"),
    "test_targeted": ("test", "targeted", "single", "file"),
    "lint": ("lint", "eslint", "clippy", "ruff", "flake8"),
    "typecheck": ("typecheck", "type-check", "types", "tsc", "mypy", "pyright", "vet"),
    "build": ("build", "compile"),
    "e2e": ("e2e", "end-to-end", "cypress", "playwright"),
    "uat": ("uat", "acceptance", "scenario"),
    "run": ("dev", "run", "start", "serve"),
}

RUNNER_RE = re.compile(
    r"^(?:sudo\s+)?(?:npm|npx|pnpm|yarn|bun|node|deno|make|just|task|uv|python3?|pytest|"
    r"poetry|pip3?|cargo|go|gradle|\./gradlew|mvn|\./mvnw|docker|docker-compose|ruff|mypy|"
    r"pyright|tsc|turbo|nx|vitest|jest|playwright|eslint|prettier|tox|nox|coverage|hatch|"
    r"pdm|rye)\b"
)

#: Discovered commands must be safe to run; deploy/publish-style CI commands are never
#: suggested as verification commands.
UNSAFE_DISCOVERY_RE = re.compile(
    r"\b(?:deploy|release|publish|push|merge|destroy|terraform|kubectl|helm|argocd|"
    r"migrate|drop\s+database|rollback)\b",
    re.IGNORECASE,
)

DOC_ORDER = ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "README.md")

TASK_RUNNERS = (
    ("Makefile", "make"),
    ("makefile", "make"),
    ("GNUmakefile", "make"),
    ("justfile", "just"),
    ("Justfile", "just"),
    ("Taskfile.yml", "task"),
    ("Taskfile.yaml", "task"),
    ("taskfile.yml", "task"),
    ("taskfile.yaml", "task"),
)

TARGET_CANDIDATES = {
    "setup": ("setup", "install", "bootstrap", "deps", "dev-setup"),
    "test": ("test", "tests", "check", "verify"),
    "test_fast": ("test-fast", "test_fast", "test:fast", "unit", "test-unit", "test:unit"),
    "test_full": (
        "test-full",
        "test_full",
        "test:full",
        "test-all",
        "test:all",
        "integration",
        "test-integration",
    ),
    "test_targeted": ("test-file", "test:file", "test-targeted", "test:targeted"),
    "lint": ("lint", "lint-check", "check-lint"),
    "typecheck": ("typecheck", "type-check", "types", "check-types"),
    "build": ("build",),
    "e2e": ("e2e", "test-e2e", "e2e-test", "test:e2e"),
    "uat": ("uat", "acceptance", "test-acceptance", "test:acceptance"),
    "run": ("run", "dev", "start", "serve"),
}

JS_SCRIPTS = {
    "setup": ("setup", "install", "bootstrap", "prepare"),
    "test": ("test",),
    "test_fast": ("test:fast", "test:unit", "test:quick", "test:watch", "test"),
    "test_full": ("test:full", "test:all", "test:ci", "test:integration", "test"),
    "test_targeted": ("test:targeted", "test:file", "test:single"),
    "lint": ("lint", "eslint", "lint:check"),
    "typecheck": ("typecheck", "type-check", "tsc", "types"),
    "build": ("build",),
    "e2e": ("e2e", "test:e2e", "cypress", "playwright"),
    "uat": ("uat", "test:acceptance", "acceptance"),
    "run": ("dev", "start", "serve"),
}

PY_LOCK_MANAGERS = (
    ("uv.lock", "uv run "),
    ("poetry.lock", "poetry run "),
    ("pdm.lock", "pdm run "),
)

DEFAULT_ADAPTER_NAME = None

DEFAULT_FIELDS = {
    "planning": {"mode": "speckit", "plan_path": None, "task_source": None},
    "repos": {},
    "worktree_name_pattern": "{repo}-wt-{slug}",
    "worktree_dir": ".worktrees",
    "branch_pattern": "{type}/{slug}",
    "commit_policy": "per-change",
    "integration": "ask",
    "output_language": None,
    "pr_template": None,
    "pr_required_sections": [],
    "tdd": "optional",
    "tdd_required_paths": [],
    "brief_dir": "docs/briefs",
    "risk_areas": [],
    "review": {"human_required_for": []},
    "tracker": "none",
    "tracker_notes": "",
    "references": [],
    "scripts": [],
}

PLANNING_MODES = ("speckit", "external", "none")
BASELINE_KINDS = ("file", "command", "prose")


class ResolveError(ValueError):
    """A resolvable problem with the adapter contents (not a parse error)."""


def _err(path, line, message):
    return FrontmatterError(message, path, line)


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _shell_word(value):
    """Render a discovered command unchanged (it is already a shell command string)."""
    return value


# --------------------------------------------------------------------------------------
# Discovery: project docs
# --------------------------------------------------------------------------------------


def _doc_candidates(text):
    """Yield ``(command, heading, line_number)`` candidates from a Markdown doc."""
    heading = ""
    in_fence = False
    for line_no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            in_fence = False
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            command = stripped.lstrip("$> ").strip()
            if command:
                yield command, heading, line_no
        else:
            for snippet in re.findall(r"`([^`\n]+)`", raw):
                yield snippet.strip(), heading, line_no


def _discover_from_docs(repo, key):
    words = DISCOVERY_WORDS[key]
    best_heading = None
    for doc_name in DOC_ORDER:
        text = _read_text(repo / doc_name)
        if not text:
            continue
        for command, heading, line_no in _doc_candidates(text):
            if not RUNNER_RE.match(command) or UNSAFE_DISCOVERY_RE.search(command):
                continue
            lowered = command.lower()
            if any(word in lowered for word in words):
                return {
                    "value": command,
                    "source": "discovered",
                    "evidence": "%s:%d: `%s`" % (doc_name, line_no, command),
                }
            if best_heading is None and any(word in heading.lower() for word in words):
                best_heading = {
                    "value": command,
                    "source": "discovered",
                    "evidence": "%s:%d (section '%s'): `%s`"
                    % (doc_name, line_no, heading, command),
                }
    return best_heading


# --------------------------------------------------------------------------------------
# Discovery: task runners
# --------------------------------------------------------------------------------------


def _makefile_targets(text):
    targets = []
    for line in text.splitlines():
        if line.startswith("\t") or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", line)
        if match:
            targets.append(match.group(1))
    return targets


def _taskfile_targets(text):
    targets = []
    in_tasks = False
    for line in text.splitlines():
        stripped = line.strip()
        if line.startswith("tasks:"):
            in_tasks = True
            continue
        if in_tasks:
            if stripped and not line.startswith((" ", "\t")):
                break
            match = re.match(r"^\s{1,4}([A-Za-z0-9_-]+):\s*$", line)
            if match:
                targets.append(match.group(1))
    return targets


def _discover_from_runners(repo, key):
    candidates = TARGET_CANDIDATES[key]
    for filename, runner in TASK_RUNNERS:
        path = repo / filename
        text = _read_text(path)
        if text is None:
            continue
        if runner == "task":
            targets = _taskfile_targets(text)
        else:
            targets = _makefile_targets(text)
        for candidate in candidates:
            if candidate in targets:
                return {
                    "value": "%s %s" % (runner, candidate),
                    "source": "discovered",
                    "evidence": "%s target '%s'" % (filename, candidate),
                }
    return None


# --------------------------------------------------------------------------------------
# Discovery: ecosystem manifests
# --------------------------------------------------------------------------------------


def _js_package_manager(repo):
    for lockfile, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("bun.lock", "bun"),
    ):
        if (repo / lockfile).exists():
            return manager
    return "npm"


def _discover_from_package_json(repo, key):
    text = _read_text(repo / "package.json")
    if text is None:
        return None
    try:
        package = json.loads(text)
    except ValueError:
        return None
    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        return None
    manager = _js_package_manager(repo)
    for candidate in JS_SCRIPTS[key]:
        if candidate not in scripts:
            continue
        if manager == "yarn":
            command = "yarn %s" % candidate
        elif manager == "pnpm":
            command = "pnpm run %s" % candidate
        elif manager == "bun":
            command = "bun run %s" % candidate
        else:
            command = "npm run %s" % candidate
        return {
            "value": command,
            "source": "discovered",
            "evidence": "package.json scripts.%s (%s)" % (candidate, manager),
        }
    return None


def _python_manager_for(repo):
    """Return ``(command_prefix, evidence)`` for the Python project, or ``(None, None)``."""
    runners = []
    for lockfile, prefix in PY_LOCK_MANAGERS:
        if (repo / lockfile).exists():
            runners.append((lockfile, prefix))
    if not runners:
        if (repo / "pyproject.toml").exists():
            return "", "pyproject.toml"
        if (repo / "requirements.txt").exists():
            return "", "requirements.txt"
        return None, None
    return runners[0][1], runners[0][0]


def _discover_from_python(repo, key):
    pyproject = _read_text(repo / "pyproject.toml")
    lockfile = next(
        ((lock, prefix) for lock, prefix in PY_LOCK_MANAGERS if (repo / lock).exists()),
        None,
    )
    if pyproject is None and lockfile is None and not (repo / "requirements.txt").exists():
        return None
    prefix, manager_evidence = _python_manager_for(repo)
    if prefix is None:
        return None
    lowered = (pyproject or "").lower()

    def result(command, evidence):
        return {
            "value": prefix + command,
            "source": "discovered",
            "evidence": evidence,
        }

    if key == "setup":
        if lockfile and lockfile[0] == "uv.lock":
            return result("uv sync", "uv.lock")
        if lockfile and lockfile[0] == "poetry.lock":
            return result("poetry install", "poetry.lock")
        if lockfile and lockfile[0] == "pdm.lock":
            return result("pdm install", "pdm.lock")
        if (repo / "requirements.txt").exists():
            return result("pip install -r requirements.txt", "requirements.txt")
        return None
    if key in ("test", "test_fast", "test_full", "test_targeted"):
        if "pytest" not in lowered and (repo / "tests").is_dir() is False:
            return None
        if key == "test_targeted":
            return result("pytest {path}", "pytest + {path} token")
        return result("pytest", manager_evidence or "pytest")
    if key == "lint":
        if "[tool.ruff" in lowered:
            return result("ruff check .", "pyproject.toml [tool.ruff]")
        if "flake8" in lowered:
            return result("flake8", "pyproject.toml flake8")
        return None
    if key == "typecheck":
        if "[tool.mypy" in lowered:
            return result("mypy .", "pyproject.toml [tool.mypy]")
        if "[tool.pyright" in lowered or (repo / "pyrightconfig.json").exists():
            return result("pyright", "pyright configuration")
        return None
    if key == "build":
        if "[build-system]" not in lowered:
            return None
        if lockfile and lockfile[0] == "uv.lock":
            return result("uv build", "pyproject.toml [build-system] + uv.lock")
        if lockfile and lockfile[0] == "poetry.lock":
            return result("poetry build", "pyproject.toml [build-system] + poetry.lock")
        return None
    return None


def _discover_from_cargo(repo, key):
    text = _read_text(repo / "Cargo.toml")
    if text is None:
        return None
    commands = {
        "test": ("cargo test", "Cargo.toml"),
        "test_fast": ("cargo test", "Cargo.toml"),
        "test_full": ("cargo test", "Cargo.toml"),
        "lint": ("cargo clippy", "Cargo.toml"),
        "typecheck": ("cargo check", "Cargo.toml"),
        "build": ("cargo build", "Cargo.toml"),
        "run": ("cargo run", "Cargo.toml"),
        "setup": (None, None),
    }
    command, evidence = commands.get(key, (None, None))
    if not command:
        return None
    return {"value": command, "source": "discovered", "evidence": evidence}


def _discover_from_go(repo, key):
    if not (repo / "go.mod").exists():
        return None
    commands = {
        "test": ("go test ./...", "go.mod"),
        "test_fast": ("go test ./...", "go.mod"),
        "test_full": ("go test ./...", "go.mod"),
        "lint": ("go vet ./...", "go.mod"),
        "typecheck": ("go vet ./...", "go.mod"),
        "build": ("go build ./...", "go.mod"),
        "setup": ("go mod download", "go.mod"),
    }
    command, evidence = commands.get(key, (None, None))
    if not command:
        return None
    return {"value": command, "source": "discovered", "evidence": evidence}


def _discover_from_manifests(repo, key):
    for finder in (
        _discover_from_package_json,
        _discover_from_python,
        _discover_from_cargo,
        _discover_from_go,
    ):
        found = finder(repo, key)
        if found:
            return found
    return None


# --------------------------------------------------------------------------------------
# Discovery: CI configuration
# --------------------------------------------------------------------------------------


def _ci_files(repo):
    files = []
    workflows = repo / ".github" / "workflows"
    if workflows.is_dir():
        for pattern in ("*.yml", "*.yaml"):
            files.extend(sorted(workflows.glob(pattern)))
    for relative in (".gitlab-ci.yml", ".circleci/config.yml", "azure-pipelines.yml"):
        candidate = repo / relative
        if candidate.is_file():
            files.append(candidate)
    return files


def _ci_commands(text):
    """Yield ``(command, line_number)`` from a CI YAML file (a pragmatic subset)."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(r"^\s*-?\s*(?:run|script|commands?):\s*(.*)$", line)
        if match:
            value = match.group(1).strip()
            line_no = index + 1
            index += 1
            if value in ("|", ">", "|-", ">-", "|+", ">+"):
                base_indent = len(line) - len(line.lstrip())
                while index < len(lines):
                    child = lines[index]
                    if child.strip() and len(child) - len(child.lstrip()) <= base_indent:
                        break
                    command = child.strip()
                    if command and not command.startswith("#"):
                        yield command, index + 1
                    index += 1
                continue
            if value:
                yield value.strip("'\""), line_no
            continue
        if re.match(r"^\s*-\s+\S", line) and not re.search(
            r"^\s*-\s*(?:name|uses|with|env|id|if):", line
        ):
            command = re.sub(r"^\s*-\s+", "", line).strip().strip("'\"")
            yield command, index + 1
        index += 1


def _discover_from_ci(repo, key):
    words = DISCOVERY_WORDS[key]
    for path in _ci_files(repo):
        text = _read_text(path)
        if not text:
            continue
        try:
            relative = str(path.relative_to(repo))
        except ValueError:
            relative = str(path)
        for command, line_no in _ci_commands(text):
            if not RUNNER_RE.match(command) or UNSAFE_DISCOVERY_RE.search(command):
                continue
            if any(word in command.lower() for word in words):
                return {
                    "value": command,
                    "source": "discovered",
                    "evidence": "%s:%d: `%s`" % (relative, line_no, command),
                }
    return None


def _discover(repo, key):
    """Return a ``{"value", "source", "evidence"}`` dict or ``None``."""
    for finder in (
        _discover_from_docs,
        _discover_from_runners,
        _discover_from_manifests,
        _discover_from_ci,
    ):
        found = finder(repo, key)
        if found:
            found["value"] = _shell_word(found["value"])
            return found
    return None


# --------------------------------------------------------------------------------------
# Static default-branch detection (read-only: no git subprocess)
# --------------------------------------------------------------------------------------


def _git_dir(repo):
    """Find the enclosing git directory; walks up so monorepo subprojects work."""
    current = repo
    for _ in range(12):
        dot_git = current / ".git"
        if dot_git.is_dir():
            return dot_git
        if dot_git.is_file():
            text = _read_text(dot_git) or ""
            match = re.match(r"gitdir:\s*(.+)", text.strip())
            if match:
                candidate = Path(match.group(1).strip())
                if not candidate.is_absolute():
                    candidate = (current / candidate).resolve()
                if candidate.is_dir():
                    return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def _detect_default_branch(repo):
    git_dir = _git_dir(repo)
    if git_dir is None:
        return None, "not a git repository (%s/.git not found)" % repo
    origin_head = _read_text(git_dir / "refs" / "remotes" / "origin" / "HEAD")
    if origin_head:
        match = re.match(r"ref:\s*refs/remotes/origin/(\S+)", origin_head.strip())
        if match:
            return match.group(1), ".git/refs/remotes/origin/HEAD"
    packed = _read_text(git_dir / "packed-refs") or ""
    for line in packed.splitlines():
        match = re.match(r"ref:\s*refs/remotes/origin/(\S+)", line.strip())
        if match:
            return match.group(1), ".git/packed-refs"
        match = re.match(r"^[0-9a-f]+\s+refs/remotes/origin/(\S+)$", line.strip())
        if match and match.group(1) != "HEAD":
            return match.group(1), ".git/packed-refs"
    head = _read_text(git_dir / "HEAD")
    if head:
        match = re.match(r"ref:\s*refs/heads/(\S+)", head.strip())
        if match:
            return match.group(1), ".git/HEAD (local branch; origin/HEAD not found)"
    return None, "no origin/HEAD or HEAD ref in .git"


# --------------------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------------------


def _adapter_paths(adapter, repo):
    """Return ``(adapter_path_or_None, repo_path, notes)``."""
    notes = []
    adapter_arg = Path(adapter).expanduser() if adapter else None
    repo_arg = Path(repo).expanduser() if repo else None
    if adapter_arg is not None:
        candidate = adapter_arg
        if candidate.is_dir():
            candidate = candidate / "adapter.md"
        candidate = candidate.resolve()
        if not candidate.is_file():
            raise ResolveError(
                "adapter file not found: %s (pass --adapter PATH to the adapter.md file "
                "or --repo to a project with .aiek/adapter.md)" % adapter_arg
            )
        if repo_arg is not None:
            repo_path = repo_arg.resolve()
        elif candidate.parent.name == ".aiek":
            repo_path = candidate.parent.parent
        else:
            repo_path = Path.cwd().resolve()
            notes.append(
                "no --repo given and the adapter is not at .aiek/adapter.md; "
                "discovering commands from %s" % repo_path
            )
        if not repo_path.is_dir():
            raise ResolveError("repo directory not found: %s" % repo_path)
        return candidate, repo_path, notes
    if repo_arg is not None:
        repo_path = repo_arg.resolve()
        if not repo_path.is_dir():
            raise ResolveError("repo directory not found: %s" % repo_arg)
        candidate = repo_path / ".aiek" / "adapter.md"
        if candidate.is_file():
            return candidate.resolve(), repo_path, notes
        notes.append(
            "no adapter file at %s; resolving defaults and discovery only" % candidate
        )
        return None, repo_path, notes
    repo_path = Path.cwd().resolve()
    candidate = repo_path / ".aiek" / "adapter.md"
    if candidate.is_file():
        return candidate.resolve(), repo_path, notes
    raise ResolveError(
        "no adapter file at %s; run install.sh first or pass --adapter/--repo" % candidate
    )


def _command_entry(value, source, evidence=None):
    return {"value": value, "source": source, "evidence": evidence}


def _validate_verify(raw_verify, adapter_display):
    if raw_verify is None:
        return {}, []
    if not isinstance(raw_verify, dict):
        raise _err(adapter_display, None, "'verify' must be a mapping of command keys")
    verified = {}
    for key in COMMAND_KEYS:
        if key not in raw_verify:
            continue
        value = raw_verify[key]
        if value is None:
            verified[key] = None
        elif isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise _err(
                    adapter_display,
                    None,
                    "verify.%s is empty; use null for 'not available' or a command" % key,
                )
            verified[key] = stripped
        else:
            raise _err(
                adapter_display,
                None,
                "verify.%s must be a command string or null (found %s)"
                % (key, type(value).__name__),
            )
    unknown = sorted(set(raw_verify) - set(COMMAND_KEYS))
    return verified, unknown


def _resolve_planning(raw, adapter_display):
    warnings = []
    data = dict(DEFAULT_FIELDS["planning"])
    if raw is MISSING or raw is None:
        return {"value": data, "source": "default"}, warnings
    if not isinstance(raw, dict):
        raise _err(adapter_display, None, "'planning' must be a mapping (mode/plan_path/task_source)")
    unknown = sorted(set(raw) - {"mode", "plan_path", "task_source"})
    for key in unknown:
        warnings.append("unknown planning key '%s' ignored (allowed: mode, plan_path, task_source)" % key)
    mode = raw.get("mode", MISSING)
    if mode is not MISSING and mode is not None:
        if mode not in PLANNING_MODES:
            raise _err(
                adapter_display,
                None,
                "planning.mode must be one of %s (found %r)"
                % (", ".join(PLANNING_MODES), mode),
            )
        data["mode"] = mode
    for key in ("plan_path", "task_source"):
        value = raw.get(key, MISSING)
        if value is not MISSING:
            if value is not None and not isinstance(value, str):
                raise _err(adapter_display, None, "planning.%s must be a path string or null" % key)
            data[key] = value
    source = "adapter" if isinstance(raw, dict) and raw else "default"
    return {"value": data, "source": source}, warnings


def _resolve_baselines(raw, raw_v1, repo, adapter_display):
    warnings = []
    entries = []
    if raw is not MISSING and raw is not None:
        if not isinstance(raw, list):
            raise _err(
                adapter_display,
                None,
                "'baselines' must be a list of {name, kind, value} mappings",
            )
        for index, entry in enumerate(raw):
            if not isinstance(entry, dict):
                raise _err(
                    adapter_display,
                    None,
                    "baselines[%d] must be a mapping with name, kind and value" % index,
                )
            kind = entry.get("kind", "file")
            if kind not in BASELINE_KINDS:
                raise _err(
                    adapter_display,
                    None,
                    "baselines[%d].kind must be one of %s (found %r)"
                    % (index, ", ".join(BASELINE_KINDS), kind),
                )
            value = entry.get("value")
            if not isinstance(value, str) or not value.strip():
                raise _err(
                    adapter_display,
                    None,
                    "baselines[%d].value must be a non-empty string" % index,
                )
            name = entry.get("name") or "baseline-%d" % (index + 1)
            if not isinstance(name, str):
                raise _err(adapter_display, None, "baselines[%d].name must be a string" % index)
            entries.append({"name": name, "kind": kind, "value": value.strip()})
        if raw_v1 is not MISSING and raw_v1 is not None:
            warnings.append("both 'baseline' and 'baselines' are set; using 'baselines'")
        source = "adapter"
    elif raw_v1 is not MISSING and raw_v1 is not None:
        if not isinstance(raw_v1, str) or not raw_v1.strip():
            raise _err(adapter_display, None, "'baseline' must be a path or prose string")
        value = raw_v1.strip()
        kind = "file" if (repo / value).is_file() else "prose"
        entries.append({"name": "baseline", "kind": kind, "value": value})
        warnings.append(
            "'baseline' is the v1 key; prefer 'baselines' (list of {name, kind, value})"
        )
        source = "adapter"
    else:
        source = "default"
    return {"value": entries, "source": source}, warnings


def _resolve_default_branch(raw, repo):
    if raw is not MISSING and raw is not None:
        if not isinstance(raw, str) or not raw.strip():
            raise ResolveError("'default_branch' must be a branch name or 'auto'")
        if raw.strip().lower() != "auto":
            return {"value": raw.strip(), "source": "adapter", "evidence": "adapter.md"}
    branch, evidence = _detect_default_branch(repo)
    if branch:
        return {"value": branch, "source": "discovered", "evidence": evidence}
    return {
        "value": None,
        "source": "unavailable",
        "evidence": evidence,
    }


def _simple_field(data, key, adapter_display, warnings):
    if key not in data or data[key] is MISSING:
        return {"value": DEFAULT_FIELDS[key], "source": "default"}
    return {"value": data[key], "source": "adapter"}


def _resolve_verify(raw_verify, repo, adapter_display):
    warnings = []
    verified, unknown = _validate_verify(raw_verify, adapter_display)
    for key in unknown:
        warnings.append("unknown verify key '%s' ignored (see core/adapter-contract.md)" % key)

    resolved = {}
    explicit_null = set()
    auto_keys = set()
    for key, value in verified.items():
        if value is None:
            explicit_null.add(key)
            resolved[key] = _command_entry(None, "adapter", "null = not available")
        elif value.strip().lower() == "auto":
            auto_keys.add(key)  # resolved with command-discovery.md
        else:
            resolved[key] = _command_entry(value, "adapter", "adapter.md")

    def discover(key):
        if key not in DISCOVERABLE_KEYS:
            return None
        found = _discover(repo, key)
        if found:
            return _command_entry(found["value"], found["source"], found["evidence"])
        return None

    # 1. test is the anchor: it drives test_fast/test_full when they are not configured.
    if "test" not in resolved and "test" not in explicit_null:
        found = discover("test")
        if found:
            resolved["test"] = found
    # 2. fast/full: explicit > discovery (specific names) > derived from test.
    for key in ("test_fast", "test_full"):
        if key in resolved or key in explicit_null:
            continue
        found = discover(key)
        if found and found["value"] and found["value"] != (resolved.get("test") or {}).get("value"):
            resolved[key] = found
        elif resolved.get("test"):
            resolved[key] = _command_entry(
                resolved["test"]["value"],
                "derived",
                "verify.test (no %s configured; use the same command)" % key,
            )
        elif found:
            resolved[key] = found
    # 3. A project that only declares test_fast/test_full still needs `test`.
    if "test" not in resolved and "test" not in explicit_null:
        for fallback in ("test_full", "test_fast"):
            entry = resolved.get(fallback)
            if entry and entry["value"]:
                resolved["test"] = _command_entry(
                    entry["value"],
                    "derived",
                    "verify.%s (no verify.test configured)" % fallback,
                )
                break
    # 4. Remaining discoverable keys.
    for key in DISCOVERABLE_KEYS:
        if key in resolved or key in explicit_null:
            continue
        found = discover(key)
        if found:
            resolved[key] = found
    # 5. Everything else is genuinely unavailable.
    unavailable = []
    for key in COMMAND_KEYS:
        if key not in resolved:
            resolved[key] = _command_entry(
                None,
                "unavailable",
                "no adapter value and no discovery match; treat as not available and "
                "list it under Remaining risks",
            )
        if (
            resolved[key]["value"] is None
            and key not in explicit_null
            and (key in DISCOVERABLE_KEYS or key == "deploy_check")
        ):
            unavailable.append(key)
    if unavailable:
        warnings.append(
            "verify command(s) unavailable (no adapter value, no discovery match): %s"
            % ", ".join(unavailable)
        )
    return resolved, warnings


def resolve_adapter(adapter=None, repo=None):
    """Resolve an adapter into the JSON-ready dict used by every helper script.

    ``adapter`` is a path to ``adapter.md`` (or its directory); ``repo`` is the project
    root used for discovery. Both may be given; ``--repo`` wins for the discovery root.
    Raises :class:`FrontmatterError` for parse errors and :class:`ResolveError` for
    structurally valid but unusable adapters.
    """
    adapter_path, repo_path, notes = _adapter_paths(adapter, repo)
    warnings = list(notes)
    data = {}
    if adapter_path is not None:
        data, _meta = load_adapter(adapter_path)
        adapter_display = str(adapter_path)
    else:
        adapter_display = str(repo_path / ".aiek" / "adapter.md")

    verify_raw = data.get("verify", MISSING)
    if verify_raw is MISSING:
        verify_raw = {}
    verify, verify_warnings = _resolve_verify(verify_raw, repo_path, adapter_display)
    warnings.extend(verify_warnings)

    planning, planning_warnings = _resolve_planning(
        data.get("planning", MISSING), adapter_display
    )
    warnings.extend(planning_warnings)

    baselines, baseline_warnings = _resolve_baselines(
        data.get("baselines", MISSING), data.get("baseline", MISSING), repo_path, adapter_display
    )
    warnings.extend(baseline_warnings)

    default_branch = _resolve_default_branch(
        data.get("default_branch", MISSING), repo_path
    )
    if default_branch["value"] is None:
        warnings.append(
            "default_branch could not be detected (%s); worktree.py will branch from HEAD"
            % default_branch["evidence"]
        )

    repos = data.get("repos", MISSING)
    if repos is MISSING:
        repos_entry = {"value": {}, "source": "default"}
    else:
        if not isinstance(repos, dict):
            raise _err(adapter_display, None, "'repos' must be a mapping of name -> path")
        for name, value in repos.items():
            if not isinstance(value, str) or not value.strip():
                raise _err(
                    adapter_display,
                    None,
                    "repos.%s must be a path string (relative to the repo root)" % name,
                )
        repos_entry = {"value": repos, "source": "adapter"}

    fields = {}
    for key in (
        "worktree_name_pattern",
        "worktree_dir",
        "branch_pattern",
        "commit_policy",
        "integration",
        "output_language",
        "pr_template",
        "pr_required_sections",
        "tdd",
        "tdd_required_paths",
        "brief_dir",
        "risk_areas",
        "review",
        "tracker",
        "tracker_notes",
        "references",
        "scripts",
    ):
        fields[key] = _simple_field(data, key, adapter_display, warnings)

    # Basic type checks for values other code relies on.
    for pattern_key in ("worktree_name_pattern", "branch_pattern", "worktree_dir"):
        value = fields[pattern_key]["value"]
        if not isinstance(value, str) or not value:
            raise ResolveError(
                "%s must be a non-empty string (found %r)" % (pattern_key, value)
            )
    for list_key in ("pr_required_sections", "tdd_required_paths", "risk_areas", "references", "scripts"):
        value = fields[list_key]["value"]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ResolveError("%s must be a list of strings" % list_key)
    if not isinstance(fields["review"]["value"], dict):
        raise ResolveError("review must be a mapping (human_required_for: [glob, ...])")

    name_raw = data.get("adapter", MISSING)
    if name_raw is MISSING or name_raw is None:
        adapter_name = {"value": DEFAULT_ADAPTER_NAME, "source": "default"}
    else:
        adapter_name = {"value": str(name_raw), "source": "adapter"}

    adapter_section = {
        "name": adapter_name,
        "path": str(adapter_path) if adapter_path is not None else None,
        "repo": str(repo_path),
        "default_branch": default_branch,
        "planning": planning,
        "repos": repos_entry,
        "verify": verify,
        "baselines": baselines,
    }
    adapter_section.update(fields)
    return {
        "schema_version": "1",
        "adapter": adapter_section,
        "warnings": warnings,
    }


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _print_human(result):
    section = result["adapter"]
    print("adapter: %s" % (section["path"] or "<none — defaults and discovery only>"))
    print("repo: %s" % section["repo"])
    print("name: %s [%s]" % (section["name"]["value"], section["name"]["source"]))
    branch = section["default_branch"]
    print(
        "default_branch: %s [%s]"
        % (branch["value"], branch["source"])
        + (" (%s)" % branch["evidence"] if branch.get("evidence") else "")
    )
    print("planning.mode: %s [%s]" % (section["planning"]["value"]["mode"], section["planning"]["source"]))
    print("verify:")
    for key in COMMAND_KEYS:
        entry = section["verify"][key]
        evidence = " (%s)" % entry["evidence"] if entry.get("evidence") else ""
        print("  %-14s %s [%s]%s" % (key + ":", entry["value"], entry["source"], evidence))
    baseline = section["baselines"]
    print("baselines: %d entry(ies) [%s]" % (len(baseline["value"]), baseline["source"]))
    print("worktree_name_pattern: %s" % section["worktree_name_pattern"]["value"])
    print("branch_pattern: %s" % section["branch_pattern"]["value"])
    print("worktree_dir: %s" % section["worktree_dir"]["value"])
    for warning in result["warnings"]:
        print("warn: %s" % warning)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="resolve_adapter.py",
        description=(
            "Resolve .aiek/adapter.md frontmatter into concrete commands. Missing or "
            "'auto' commands are discovered with core/command-discovery.md. Read-only: "
            "no project command is executed and no file is written."
        ),
        epilog=(
            "Exit codes: 0 = resolved, 1 = adapter/repo error, 2 = bad usage. "
            "Examples: resolve_adapter.py --adapter .aiek/adapter.md --json | "
            "resolve_adapter.py --repo ."
        ),
    )
    parser.add_argument(
        "--adapter",
        metavar="PATH",
        help="adapter.md file (or its directory); defaults to <repo>/.aiek/adapter.md",
    )
    parser.add_argument(
        "--repo",
        metavar="PATH",
        help="project root used for discovery (default: parent of .aiek/, else cwd)",
    )
    parser.add_argument(
        "--json", action="store_true", help="print machine-readable JSON (includes sources)"
    )
    args = parser.parse_args(argv)
    try:
        result = resolve_adapter(args.adapter, args.repo)
    except (FrontmatterError, ResolveError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
