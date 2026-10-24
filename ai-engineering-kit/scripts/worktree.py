#!/usr/bin/env python3
"""Create a guarded git worktree for a task, following the adapter's naming conventions.

Resolves ``worktree_dir`` / ``worktree_name_pattern`` / ``branch_pattern`` from
``.aiek/adapter.md`` (tokens ``{repo}``, ``{slug}``, ``{ticket}``, ``{feature}``,
``{type}``), then runs ``git worktree add -b <branch> <path> <base>`` and optionally:

* ``--copy SRC``: copy project artifacts (e.g. ``.env.example``) into the new worktree;
* ``--setup``: run the adapter's ``verify.setup`` in the new worktree;
* ``--baseline``: run the adapter's fast test command once and record the baseline.

Guards, by design:

* the target path must be inside the repository and must not already exist;
* ``--force`` is not supported and there is **no code path that removes a worktree** —
  this script never deletes anything, not even on failure;
* every git/setup/baseline command is printed before it runs;
* ``--dry-run`` prints the plan and executes nothing, writing nothing.

Exit codes: 0 = worktree ready, 1 = refusal/failure, 2 = bad usage.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _adapter_yaml import FrontmatterError  # noqa: E402
from resolve_adapter import ResolveError, resolve_adapter  # noqa: E402
from verify import dangerous_reason, run_command  # noqa: E402

TOKEN_RE = re.compile(r"\{([a-z_]+)\}")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")

SUPPORTED_TOKENS = ("repo", "slug", "ticket", "feature", "type")


class WorktreeError(ValueError):
    """A guard refused to create the worktree; the message says how to fix it."""


def _validate_token_value(name, value):
    if not value:
        return value
    if not SAFE_TOKEN_RE.match(value) or ".." in value:
        raise WorktreeError(
            "--%s must match %s and must not contain '..' (got %r)"
            % (name, SAFE_TOKEN_RE.pattern, value)
        )
    return value


def _expand(pattern, tokens, label):
    def replace(match):
        token = match.group(1)
        if token not in SUPPORTED_TOKENS:
            raise WorktreeError(
                "unsupported token {%s} in %s (supported: %s)"
                % (token, label, ", ".join("{%s}" % name for name in SUPPORTED_TOKENS))
            )
        value = tokens.get(token, "")
        if not value:
            flag = {"feature": "--feature", "ticket": "--ticket", "type": "--type"}.get(
                token, "--%s" % token
            )
            raise WorktreeError(
                "%s uses {%s} but %s was not provided (or is empty)" % (label, token, flag)
            )
        return value

    expanded = TOKEN_RE.sub(replace, pattern)
    if not expanded:
        raise WorktreeError("%s expands to an empty string" % label)
    if "{" in expanded or "}" in expanded:
        raise WorktreeError(
            "%s contains an unmatched brace after token expansion: %r" % (label, expanded)
        )
    return expanded


def _git(repo, *arguments):
    return ["git", "-C", str(repo)] + list(arguments)


def _print_command(argv, stream):
    print("+ " + shlex.join(argv), file=stream, flush=True)


def _run_argv(argv, stream, cwd=None, expect_failure=False):
    _print_command(argv, stream)
    try:
        process = subprocess.run(
            argv,
            cwd=str(cwd) if cwd is not None else None,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print("  [FAIL] could not start: %s" % exc, file=stream, flush=True)
        return 1, "", str(exc)
    output = (process.stdout or "").strip()
    errors = (process.stderr or "").strip()
    for line in (output.splitlines()[-20:] if output else []):
        print("  " + line, file=stream, flush=True)
    for line in (errors.splitlines()[-20:] if errors else []):
        print("  | " + line, file=stream, flush=True)
    if process.returncode == 0:
        print("  [ok] exit 0", file=stream, flush=True)
    elif expect_failure:
        print("  [ok] not present (expected)", file=stream, flush=True)
    else:
        print("  [FAIL] exit %d" % process.returncode, file=stream, flush=True)
    return process.returncode, output, errors


def _is_git_repo(repo):
    dot_git = repo / ".git"
    return dot_git.is_dir() or dot_git.is_file()


def _worktree_ignored(repo, worktree_dir):
    """Return True when ``worktree_dir`` is covered by the repository's .gitignore."""
    gitignore = repo / ".gitignore"
    try:
        lines = gitignore.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    normalized = worktree_dir.strip("/")
    bases = {normalized, normalized + "/", "/" + normalized + "/"}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        if stripped in bases or stripped.rstrip("/") == normalized:
            return True
        if stripped == "/" + normalized + "/":
            return True
    return False


def create_worktree(
    adapter=None,
    repo=None,
    slug=None,
    ticket=None,
    feature=None,
    type_=None,
    setup=False,
    baseline=False,
    copies=None,
    dry_run=False,
    json_output=False,
    timeout=600,
):
    """Create the worktree; returns the process exit code (0/1/2)."""
    stream = sys.stderr if json_output else sys.stdout
    warnings = []
    copies = copies or []
    try:
        resolved = resolve_adapter(adapter=adapter, repo=repo)
    except (FrontmatterError, ResolveError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    adapter_section = resolved["adapter"]
    if resolved["warnings"]:
        warnings.extend(resolved["warnings"])
    repo_root = Path(adapter_section["repo"])
    try:
        repo_root = repo_root.resolve(strict=True)
    except OSError as exc:
        print("error: cannot resolve repo path: %s" % exc, file=sys.stderr)
        return 1
    if not _is_git_repo(repo_root):
        print(
            "error: not a git repository: %s; worktree.py must run against the git "
            "repository root (run install.sh in that repository first)" % repo_root,
            file=sys.stderr,
        )
        return 1

    if not slug:
        print("error: --slug is required", file=sys.stderr)
        return 2
    try:
        slug = _validate_token_value("slug", slug)
        ticket = _validate_token_value("ticket", ticket) if ticket else None
        feature = _validate_token_value("feature", feature) if feature else None
        type_ = _validate_token_value("type", type_) if type_ else None
        tokens = {
            "repo": repo_root.name,
            "slug": slug,
            "ticket": ticket or "",
            "feature": feature or slug,
            "type": type_ or "feature",
        }
        name = _expand(
            adapter_section["worktree_name_pattern"]["value"], tokens, "worktree_name_pattern"
        )
        branch = _expand(
            adapter_section["branch_pattern"]["value"], tokens, "branch_pattern"
        )
        worktree_dir = adapter_section["worktree_dir"]["value"]
        if "/" in name or "\\" in name or name in (".", ".."):
            raise WorktreeError(
                "worktree_name_pattern produced %r; it must be a single path component"
                % name
            )
        if not BRANCH_RE.match(branch) or ".." in branch or branch.startswith("/"):
            raise WorktreeError(
                "branch_pattern produced %r, which is not a safe branch name" % branch
            )
        if Path(worktree_dir).is_absolute():
            raise WorktreeError(
                "worktree_dir must be relative to the repository (got %r)" % worktree_dir
            )
        base_dir = (repo_root / worktree_dir).resolve()
        try:
            base_dir.relative_to(repo_root)
        except ValueError:
            raise WorktreeError(
                "worktree_dir %r escapes the repository; choose a relative directory inside it"
                % worktree_dir
            ) from None
        target = base_dir / name
        try:
            target.resolve().relative_to(repo_root)
        except ValueError:
            raise WorktreeError(
                "worktree path %r escapes the repository" % target
            ) from None

        if target.exists() or target.is_symlink():
            raise WorktreeError(
                "worktree path already exists: %s\n"
                "  choose another --slug, or remove/inspect that directory yourself: "
                "worktree.py never deletes worktrees." % target
            )
        if target == repo_root:
            raise WorktreeError("worktree path would be the repository itself")

        base_branch = adapter_section["default_branch"]["value"] or "HEAD"

        copy_sources = []
        for source in copies:
            source_path = Path(source)
            if source_path.is_absolute():
                raise WorktreeError(
                    "--copy expects a path relative to the repository (got %s)" % source
                )
            absolute = (repo_root / source_path).resolve()
            try:
                relative = absolute.relative_to(repo_root)
            except ValueError:
                raise WorktreeError(
                    "--copy path escapes the repository: %s" % source
                ) from None
            if not absolute.exists():
                raise WorktreeError("--copy path does not exist: %s" % source)
            destination = target / relative
            copy_sources.append((absolute, destination, relative))

        setup_command = None
        if setup:
            setup_entry = adapter_section["verify"]["setup"]
            setup_command = setup_entry["value"]
            if not setup_command:
                raise WorktreeError(
                    "--setup requested but the adapter has no verify.setup command; "
                    "add verify.setup or run the bootstrap step manually"
                )
            reason = dangerous_reason(setup_command)
            if reason:
                raise WorktreeError(
                    "refusing verify.setup command %r: %s" % (setup_command, reason)
                )
        baseline_command = None
        if baseline:
            for key in ("test_fast", "test"):
                candidate = adapter_section["verify"][key]["value"]
                if candidate:
                    baseline_command = candidate
                    break
            if not baseline_command:
                raise WorktreeError(
                    "--baseline requested but the adapter has no verify.test_fast or "
                    "verify.test command"
                )
            reason = dangerous_reason(baseline_command)
            if reason:
                raise WorktreeError(
                    "refusing baseline command %r: %s" % (baseline_command, reason)
                )
    except WorktreeError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    if not _worktree_ignored(repo_root, worktree_dir):
        warnings.append(
            "worktree_dir '%s' is not listed in .gitignore; add it so worktrees never show "
            "up as untracked files" % worktree_dir
        )
    if adapter_section["repos"]["value"]:
        warnings.append(
            "adapter declares repos %s; worktree.py creates one worktree in %s only — "
            "create the other repositories' worktrees manually"
            % (", ".join(sorted(adapter_section["repos"]["value"])), repo_root.name)
        )

    branch_check = _git(
        repo_root, "rev-parse", "--verify", "--quiet", "refs/heads/%s" % branch
    )
    base_check = (
        _git(repo_root, "rev-parse", "--verify", "--quiet", base_branch + "^{commit}")
        if base_branch != "HEAD"
        else None
    )

    def _add_command(base):
        return _git(
            repo_root, "worktree", "add", "-b", branch, str(target), base
        )
    plan = {
        "repo": str(repo_root),
        "adapter": adapter_section["path"],
        "worktree": {
            "path": str(target),
            "name": name,
            "branch": branch,
            "base": base_branch,
            "worktree_dir": worktree_dir,
        },
        "copies": [str(destination) for _source, destination, _relative in copy_sources],
        "setup": setup_command,
        "baseline": baseline_command,
        "warnings": warnings,
        "commands": [],
    }
    if dry_run:
        print(
            "[dry-run] worktree plan (nothing will be created or executed):",
            file=stream,
        )
        print("[dry-run] would check branch absence:", file=stream)
        print("  [dry-run] " + shlex.join(branch_check), file=stream)
        print("[dry-run] would create the worktree:", file=stream)
        print("  [dry-run] " + shlex.join(_add_command(base_branch)), file=stream)
        for source, destination, _relative in copy_sources:
            print(
                "[dry-run] would copy %s -> %s" % (source, destination), file=stream
            )
        if setup_command:
            print("[dry-run] would run setup: %s" % setup_command, file=stream)
        if baseline_command:
            print("[dry-run] would run baseline: %s" % baseline_command, file=stream)
        for warning in warnings:
            print("warn: %s" % warning, file=stream)
        plan["dry_run"] = True
        plan["ok"] = True
        plan["status"] = "planned"
        if json_output:
            print(json.dumps(plan, indent=2, ensure_ascii=False))
        else:
            print("dry-run: %s (branch %s)" % (target, branch))
        return 0

    result = {"dry_run": False, "ok": False, "status": "failed"}
    result.update(plan)

    print("AI Engineering Kit worktree → %s" % target, file=stream)
    print("branch: %s (base: %s)" % (branch, base_branch), file=stream)
    for warning in warnings:
        print("warn: %s" % warning, file=stream)

    # 1. Branch must not exist yet; creating it is the whole point, so refuse early.
    returncode, output, _errors = _run_argv(branch_check, stream, expect_failure=True)
    if returncode == 0:
        print(
            "error: branch '%s' already exists; choose another --slug/--ticket or use the "
            "existing branch manually (worktree.py never reuses or force-overwrites branches)"
            % branch,
            file=sys.stderr,
        )
        return 1

    # 2. Fall back to HEAD if the adapter's default branch is not present locally.
    if base_check is not None:
        base_returncode, _output, _errors = _run_argv(
            base_check, stream, expect_failure=False
        )
        if base_returncode != 0:
            warnings.append(
                "base branch '%s' was not found locally; branching from HEAD instead"
                % base_branch
            )
            print("warn: %s" % warnings[-1], file=stream)
            base_branch = "HEAD"
            plan["worktree"]["base"] = "HEAD"
    add_command = _add_command(base_branch)

    # 3. Create the worktree. Failure leaves whatever git created; nothing is deleted.
    returncode, output, errors = _run_argv(add_command, stream)
    if returncode != 0:
        print(
            "error: git worktree add failed; a partial directory may exist at %s — inspect "
            "it and clean up manually (worktree.py never deletes)" % target,
            file=sys.stderr,
        )
        result["error"] = errors or output
        if json_output:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    # 4. Copy requested artifacts.
    for source, destination, relative in copy_sources:
        destination.parent.mkdir(parents=True, exist_ok=True)
        print(
            "+ cp -R %s %s" % (shlex.quote(str(source)), shlex.quote(str(destination))),
            file=stream,
            flush=True,
        )
        try:
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)
        except OSError as exc:
            print("  [FAIL] copy failed: %s" % exc, file=sys.stderr)
            result["error"] = str(exc)
            if json_output:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1
        print("  [ok] copied %s" % relative, file=stream, flush=True)
        result.setdefault("copies_done", []).append(str(destination))

    # 5. Setup the fresh worktree (a failure here is fatal: the worktree is not usable).
    if setup_command:
        print("setup in %s:" % target, file=stream)
        setup_result = run_command(setup_command, target, timeout, stream=stream)
        result["setup_result"] = {
            "command": setup_command,
            "status": setup_result["status"],
            "exit_code": setup_result["exit_code"],
            "duration_s": setup_result["duration_s"],
        }
        if setup_result["status"] != "pass":
            print(
                "error: verify.setup failed in the new worktree (%s); fix it and run the "
                "command manually — the worktree was left in place for inspection"
                % setup_result["status"],
                file=sys.stderr,
            )
            result["status"] = "setup_failed"
            if json_output:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1

    # 6. Record the baseline. Known failures are allowed at baseline time.
    if baseline_command:
        print("baseline in %s:" % target, file=stream)
        baseline_result = run_command(baseline_command, target, timeout, stream=stream)
        result["baseline_result"] = {
            "command": baseline_command,
            "status": baseline_result["status"],
            "exit_code": baseline_result["exit_code"],
            "duration_s": baseline_result["duration_s"],
        }
        if baseline_result["status"] != "pass":
            warnings.append(
                "baseline command finished with status %s; record it as a known-accepted "
                "failure in the adapter's baselines, or fix it before executing-task"
                % baseline_result["status"]
            )
            print("warn: %s" % warnings[-1], file=stream)

    # 7. Confirm the checked-out branch (read-only).
    verify_branch = _git(target, "rev-parse", "--abbrev-ref", "HEAD")
    returncode, checked_branch, _errors = _run_argv(verify_branch, stream)
    if returncode != 0 or checked_branch != branch:
        warnings.append(
            "could not confirm the checked-out branch (expected %r, git said %r)"
            % (branch, checked_branch)
        )

    result["worktree"]["checked_out_branch"] = checked_branch or None
    result["ok"] = True
    result["status"] = "created"
    result["warnings"] = warnings
    print("", file=stream)
    print("worktree ready: %s" % target, file=stream)
    print("  branch: %s" % branch, file=stream)
    print("  next: cd %s" % target, file=stream)
    for warning in warnings:
        print("  warn: %s" % warning, file=stream)
    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if any(argument in ("--force", "-f") for argument in argv):
        print(
            "error: worktree.py never force-creates, force-checks-out or deletes worktrees; "
            "resolve conflicts by choosing another --slug or by cleaning up manually",
            file=sys.stderr,
        )
        return 2
    parser = argparse.ArgumentParser(
        prog="worktree.py",
        description=(
            "Create a git worktree using the adapter's worktree_dir, "
            "worktree_name_pattern and branch_pattern. Prints every command, never forces, "
            "never deletes, and does nothing on --dry-run."
        ),
        epilog=(
            "Tokens: {repo}, {slug}, {ticket}, {feature}, {type}. "
            "Exit codes: 0 = ready, 1 = refusal/failure, 2 = bad usage. "
            "Example: worktree.py --adapter .aiek/adapter.md --slug ticket-ac "
            "--ticket OSA-123 --setup --baseline --dry-run"
        ),
    )
    parser.add_argument(
        "--adapter",
        metavar="PATH",
        help="adapter.md file (or directory); default <repo>/.aiek/adapter.md",
    )
    parser.add_argument("--repo", metavar="PATH", help="git repository root")
    parser.add_argument("--slug", required=True, metavar="NAME", help="short task name, e.g. ticket-ac")
    parser.add_argument("--ticket", metavar="ID", help="tracker ticket id, e.g. OSA-123")
    parser.add_argument(
        "--feature", metavar="NAME", help="Spec Kit feature directory name (for {feature})"
    )
    parser.add_argument(
        "--type", metavar="NAME", help="branch type for {type}, e.g. feature or fix (default: feature)"
    )
    parser.add_argument(
        "--copy",
        action="append",
        default=[],
        metavar="SRC",
        help="copy a repo-relative file/dir into the new worktree (repeatable)",
    )
    parser.add_argument("--setup", action="store_true", help="run verify.setup in the worktree")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="run verify.test_fast (or verify.test) once in the worktree",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan and create/execute nothing",
    )
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        metavar="N",
        help="per-command timeout in seconds for setup/baseline (default: 600)",
    )
    arguments = parser.parse_args(argv)
    if arguments.timeout <= 0:
        parser.error("--timeout must be a positive number of seconds")
    return create_worktree(
        adapter=arguments.adapter,
        repo=arguments.repo,
        slug=arguments.slug,
        ticket=arguments.ticket,
        feature=arguments.feature,
        type_=arguments.type,
        setup=arguments.setup,
        baseline=arguments.baseline,
        copies=arguments.copy,
        dry_run=arguments.dry_run,
        json_output=arguments.json,
        timeout=arguments.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
