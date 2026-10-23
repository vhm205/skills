#!/usr/bin/env python3
"""Run an adapter's verification commands and write DONE-ready evidence.

Selects ``verify.*`` commands from ``.aiek/adapter.md`` (resolved with
``core/command-discovery.md`` when a value is missing or ``auto``), prints every command
before running it, captures exit code plus a bounded output tail, compares known-accepted
failures against the adapter's ``baselines``, and writes ``evidence.md`` / ``evidence.json``.

Safety rules, enforced here rather than left to the agent:

* read-only by default: only the selected verification commands are executed;
* every command is printed before it runs;
* deploy / release / publish / merge / push / destroy / migration / cloud-CLI style
  commands are refused with a reason — they are never executed, even if an adapter says so;
* ``--dry-run`` prints the plan and executes nothing, writing no evidence;
* commands run with a timeout and a non-interactive stdin; no secret is read or printed.

Exit codes: 0 = pass, 1 = failure/refusal/unavailable selection, 2 = bad usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _adapter_yaml import FrontmatterError  # noqa: E402
from resolve_adapter import COMMAND_KEYS, ResolveError, resolve_adapter  # noqa: E402

SCOPE_CHANGED = ("lint", "typecheck", "test_fast")
SCOPE_ALL = ("lint", "typecheck", "build", "test_full", "e2e", "uat")

#: Keys that are never executed automatically, even with --only: they touch a deployed
#: environment. The skills handle those manually.
BLOCKED_KEYS = frozenset(("deploy_check",))

#: First-token commands that are destructive or publish/merge actions.
DANGEROUS_ACTIONS = frozenset(
    (
        "deploy",
        "deployment",
        "release",
        "publish",
        "push",
        "merge",
        "destroy",
        "teardown",
        "terminate",
        "rollback",
        "promote",
        "migrate",
        "dropdb",
        "truncate",
    )
)

#: First-token CLIs that are cloud/infrastructure actions.
DANGEROUS_CLIS = frozenset(
    (
        "kubectl",
        "helm",
        "argocd",
        "k9s",
        "terraform",
        "pulumi",
        "terragrunt",
        "aws",
        "gcloud",
        "firebase",
        "vercel",
        "netlify",
        "heroku",
        "systemctl",
        "shutdown",
        "reboot",
        "flyctl",
    )
)

#: (binary, subcommand) pairs that publish or rewrite history.
DANGEROUS_PAIRS = frozenset(
    (
        ("git", "push"),
        ("git", "merge"),
        ("git", "rebase"),
        ("git", "reset"),
        ("gh", "merge"),
        ("npm", "publish"),
        ("pnpm", "publish"),
        ("yarn", "publish"),
        ("bun", "publish"),
        ("cargo", "publish"),
        ("mvn", "deploy"),
        ("gradle", "publish"),
        ("docker", "push"),
        ("podman", "push"),
        ("npx", "publish"),
    )
)

#: Argument tokens that make a database/migration call destructive.
DANGEROUS_ARGS = frozenset(
    ("migrate", "migration", "downgrade", "drop", "dropdb", "reset", "flush", "deploy")
)

_DATABASE_RE = re.compile(
    r"\b(?:drop\s+(?:database|table|schema)|dropdb|truncate\s+table)\b", re.IGNORECASE
)
_FORCE_RE = re.compile(r"(?:^|\s)--force(?:=|\s|$)")
_RM_RF_RE = re.compile(r"\brm\s+-(?:[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)\b", re.IGNORECASE)


def _segments(command):
    """Split a shell command into simple segments (best effort for safety scanning)."""
    return [segment for segment in re.split(r"&&|\|\||[;|]", command) if segment.strip()]


def _tokens(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _token_name(token):
    name = os.path.basename(token).lower()
    if name.endswith(".py"):
        name = name[:-3]
    return name


def _segment_reason(segment, depth=0):
    """Check one simple shell segment (no ``&&``/``;``/``|``) for dangerous actions."""
    tokens = _tokens(segment.strip())
    if not tokens:
        return None
    index = 0
    # Skip leading environment assignments (FOO=bar cmd) and wrappers.
    while index < len(tokens) and "=" in tokens[index] and not tokens[index].startswith("-"):
        index += 1
    if index >= len(tokens):
        return None
    if _token_name(tokens[index]) in ("env", "command", "exec") and index + 1 < len(tokens):
        index += 1
    first = _token_name(tokens[index])
    if first in ("bash", "sh", "zsh"):
        if "-c" in tokens and depth < 3:
            inner_tokens = tokens[tokens.index("-c") + 1 :]
            if inner_tokens:
                reason = dangerous_reason(" ".join(inner_tokens))
                if reason:
                    return reason
        return None
    if first in DANGEROUS_ACTIONS:
        return "command starts with '%s' (deploy/release/publish/merge/destructive)" % first
    if first in DANGEROUS_CLIS:
        return "command uses the infrastructure CLI '%s'" % first
    following = _token_name(tokens[index + 1]) if index + 1 < len(tokens) else ""
    third = _token_name(tokens[index + 2]) if index + 2 < len(tokens) else ""
    if (first, following) in DANGEROUS_PAIRS:
        return "command runs '%s %s' (publish/merge/destructive)" % (first, following)
    if first == "gh":
        if following in ("release", "deploy", "publish"):
            return "command runs the GitHub CLI release/deploy action ('gh %s')" % following
        if following == "pr" and third in ("merge", "close"):
            return "command runs the GitHub CLI action 'gh pr %s'" % third
    if first in ("npm", "pnpm", "yarn", "bun") and following in ("run", "run-s"):
        script = _token_name(tokens[index + 2]) if index + 2 < len(tokens) else ""
        if script in DANGEROUS_ACTIONS:
            return "command runs the '%s' script '%s'" % (first, script)
    if first in ("make", "just", "task", "mvn", "gradle"):
        if following in DANGEROUS_ACTIONS:
            return "command runs the '%s' target '%s'" % (first, following)
    if first in ("prisma", "alembic", "rails", "sequelize", "knex", "flyway", "liquibase"):
        for argument in tokens[index + 1 :]:
            if _token_name(argument) in DANGEROUS_ARGS:
                return "command runs a database migration/drop action ('%s %s')" % (
                    first,
                    argument,
                )
    if first in ("python", "python3", "uv", "poetry"):
        rest = tokens[index + 1 :]
        if "manage.py" in rest:
            for argument in rest[rest.index("manage.py") + 1 :]:
                if _token_name(argument) in DANGEROUS_ARGS:
                    return "command runs a Django management migrate/drop action"
    return None


def dangerous_reason(command):
    """Return a human reason when a command must never be executed, else ``None``."""
    if not command or not command.strip():
        return "empty command"
    if _DATABASE_RE.search(command):
        return "command contains a database drop/truncate action"
    if _RM_RF_RE.search(command):
        return "command removes files recursively ('rm -rf')"
    if _FORCE_RE.search(command):
        return "command passes --force"
    for segment in _segments(command):
        reason = _segment_reason(segment)
        if reason:
            return reason
    return None


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tail(text, max_lines=40, max_chars=4000):
    if not text:
        return ""
    lines = text.rstrip().splitlines()
    tail = "\n".join(lines[-max_lines:])
    return tail[-max_chars:]


def run_command(command, repo, timeout, stream=None):
    """Run one shell command, capturing a bounded result. Returns a result dict.

    Public (not underscore-prefixed) so worktree.py can reuse the same runner and safety
    semantics for ``verify.setup`` / baseline commands.
    """
    if stream is None:
        stream = sys.stdout
    started = time.monotonic()
    display = command
    result = {
        "command": display,
        "exit_code": None,
        "duration_s": 0.0,
        "stdout_tail": "",
        "stderr_tail": "",
        "timed_out": False,
        "status": "fail",
        "error": None,
    }
    print("+ %s" % display, file=stream, flush=True)
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=str(repo),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        result["error"] = "could not start command: %s" % exc
        result["duration_s"] = round(time.monotonic() - started, 2)
        print("  [FAIL] could not start: %s" % exc, file=stream, flush=True)
        return result
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        result["timed_out"] = True
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:  # pragma: no cover - non-POSIX fallback
                process.kill()
        except OSError:
            process.kill()
        stdout, stderr = process.communicate()
    result["duration_s"] = round(time.monotonic() - started, 2)
    result["exit_code"] = process.returncode
    result["stdout_tail"] = _tail(stdout)
    result["stderr_tail"] = _tail(stderr)
    if result["timed_out"]:
        result["status"] = "timeout"
        print("  [TIMEOUT] killed after %ss" % timeout, file=stream, flush=True)
    elif process.returncode == 0:
        result["status"] = "pass"
        print("  [pass] exit 0 in %ss" % result["duration_s"], file=stream, flush=True)
    else:
        result["status"] = "fail"
        print(
            "  [FAIL] exit %s in %ss" % (process.returncode, result["duration_s"]),
            file=stream,
            flush=True,
        )
    if result["status"] != "pass":
        combined = result["stderr_tail"] or result["stdout_tail"]
        for line in combined.splitlines()[-20:]:
            print("  | " + line, file=stream, flush=True)
    return result


def _load_baselines(resolved, repo, warnings):
    """Classify adapter baselines into file entries, prose notes and command notes."""
    entries = resolved["adapter"]["baselines"]["value"]
    file_entries = []
    prose_entries = []
    command_entries = []
    for entry in entries:
        kind = entry["kind"]
        value = entry["value"]
        if kind == "file":
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = repo / path
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                warnings.append(
                    "baseline file not found or unreadable: %s; treating it as prose that a "
                    "human must compare" % path
                )
                prose_entries.append(entry)
                continue
            accepted = []
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                accepted.append(stripped)
            file_entries.append({"name": entry["name"], "path": str(path), "entries": accepted})
        elif kind == "prose":
            prose_entries.append(entry)
        else:  # kind == command: reported, never executed by verify.py
            command_entries.append(entry)
    if command_entries:
        warnings.append(
            "baseline command(s) are not executed by verify.py; compare them manually: "
            + ", ".join(entry["name"] for entry in command_entries)
        )
    return {
        "file_entries": file_entries,
        "prose_entries": prose_entries,
        "command_entries": command_entries,
    }


def _resolve_selection(resolved, scope, only):
    """Return the ordered list of ``(key, command)`` selected by scope/--only."""
    available = {}
    for key in COMMAND_KEYS:
        entry = resolved["adapter"]["verify"][key]
        if entry["value"]:
            available[key] = entry
    if only:
        missing = [key for key in only if key not in available]
        if missing:
            return None, (
                "command(s) %s are not available in the adapter; available: %s"
                % (", ".join(missing), ", ".join(sorted(available)) or "<none>")
            )
        selected_keys = [key for key in only if key in available]
    else:
        keys = SCOPE_CHANGED if scope == "changed" else SCOPE_ALL
        selected_keys = [key for key in keys if key in available]
        if scope == "changed" and "test_fast" not in available and "test" in available:
            selected_keys = [
                "test" if key == "test_fast" else key for key in selected_keys
            ]
            selected_keys = list(dict.fromkeys(selected_keys))
        if scope == "all" and "test_full" not in available and "test" in available:
            selected_keys = ["test" if key == "test_full" else key for key in selected_keys]
            selected_keys = list(dict.fromkeys(selected_keys))
    selected = []
    for key in selected_keys:
        entry = available[key]
        blocked = None
        if key in BLOCKED_KEYS:
            blocked = (
                "verify.%s touches a deployed environment; verify.py never runs it"
                % key
            )
        else:
            reason = dangerous_reason(entry["value"])
            if reason:
                blocked = reason
        selected.append(
            {
                "key": key,
                "command": entry["value"],
                "adapter_source": entry["source"],
                "adapter_evidence": entry.get("evidence"),
                "refused_reason": blocked,
            }
        )
    return selected, None


def _write_evidence(evidence_dir, payload, results):
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    json_path = evidence_dir / "evidence.json"
    markdown_path = evidence_dir / "evidence.md"
    json_tmp = evidence_dir / ".evidence.json.tmp"
    json_tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(json_tmp, json_path)

    lines = []
    lines.append("# Verification evidence")
    lines.append("")
    lines.append("- generated: %s" % payload["finished_at"])
    lines.append("- adapter: %s" % (payload["adapter"] or "<defaults/discovery>"))
    lines.append("- repo: %s" % payload["repo"])
    lines.append("- scope: %s" % payload["scope"])
    lines.append("- result: **%s**" % payload["result"].upper())
    lines.append("- command: `bash .aiek/scripts/verify.py --adapter .aiek/adapter.md`")
    lines.append("")
    lines.append("| # | check | command | exit | status | duration |")
    lines.append("|---|---|---|---|---|---|")
    for index, result in enumerate(results, 1):
        lines.append(
            "| %d | %s | `%s` | %s | %s | %ss |"
            % (
                index,
                result["key"],
                result["command"],
                result["exit_code"],
                result["status"],
                result["duration_s"],
            )
        )
    for warning in payload["warnings"]:
        lines.append("")
        lines.append("> warning: %s" % warning)
    for result in results:
        lines.append("")
        lines.append("## %s — %s" % (result["key"], result["status"]))
        lines.append("")
        if result.get("error"):
            lines.append("error: %s" % result["error"])
        lines.append("```")
        lines.append("$ %s" % result["command"])
        if result["stdout_tail"]:
            lines.append(result["stdout_tail"])
        if result["stderr_tail"]:
            lines.append("# stderr:")
            lines.append(result["stderr_tail"])
        lines.append("```")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def verify(adapter=None, repo=None, scope="changed", only=None, json_output=False,
           dry_run=False, timeout=600, evidence_dir=None):
    """Run adapter verification commands; returns the process exit code (0/1/2)."""
    warnings = []
    try:
        resolved = resolve_adapter(adapter=adapter, repo=repo)
    except (FrontmatterError, ResolveError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    warnings.extend(resolved["warnings"])
    repo_path = Path(resolved["adapter"]["repo"])
    adapter_path = resolved["adapter"]["path"]

    only_keys = None
    if only:
        only_keys = [key.strip() for key in only.split(",") if key.strip()]
        if not only_keys:
            print("error: --only needs at least one command key", file=sys.stderr)
            return 2
        unknown = [key for key in only_keys if key not in COMMAND_KEYS]
        if unknown:
            print(
                "error: unknown --only key(s): %s (known: %s)"
                % (", ".join(unknown), ", ".join(COMMAND_KEYS)),
                file=sys.stderr,
            )
            return 2
        only_keys = list(dict.fromkeys(only_keys))

    selected, selection_error = _resolve_selection(resolved, scope, only_keys)
    if selection_error:
        print("error: %s" % selection_error, file=sys.stderr)
        return 1
    if not selected:
        print(
            "error: no verification commands available for scope '%s'; set verify.* in %s "
            "or pass --only with an available key (discovered commands can be inspected "
            "with resolve_adapter.py --json)"
            % (scope, adapter_path or ".aiek/adapter.md"),
            file=sys.stderr,
        )
        return 1

    baselines = _load_baselines(resolved, repo_path, warnings)
    if baselines["prose_entries"]:
        warnings.append(
            "prose baseline(s) require a human comparison; verify.py records them in the "
            "evidence but cannot auto-accept failures: %s"
            % ", ".join(entry["name"] for entry in baselines["prose_entries"])
        )
    if evidence_dir is None:
        evidence_dir = repo_path / ".aiek" / "evidence"
    else:
        evidence_dir = Path(evidence_dir).expanduser()
        if not evidence_dir.is_absolute():
            evidence_dir = repo_path / evidence_dir
    started_at = _now()
    started = time.monotonic()

    if dry_run:
        if json_output:
            stream = sys.stderr
        else:
            stream = sys.stdout
        print(
            "[dry-run] scope=%s: %d command(s) selected; nothing will be executed and no "
            "evidence will be written" % (scope, len(selected)),
            file=stream,
        )
        for item in selected:
            if item["refused_reason"]:
                print(
                    "[dry-run] REFUSED %s: %s (%s)"
                    % (item["key"], item["command"], item["refused_reason"]),
                    file=stream,
                )
            else:
                print("[dry-run] would run %s: %s" % (item["key"], item["command"]), file=stream)
        refused = [item for item in selected if item["refused_reason"]]
        payload = {
            "schema_version": "1",
            "tool": "verify.py",
            "dry_run": True,
            "result": "refused" if refused else "planned",
            "scope": scope,
            "adapter": adapter_path,
            "repo": str(repo_path),
            "commands": [
                {
                    "key": item["key"],
                    "command": item["command"],
                    "source": item["adapter_source"],
                    "status": "refused" if item["refused_reason"] else "planned",
                    "refused_reason": item["refused_reason"],
                }
                for item in selected
            ],
            "warnings": warnings,
        }
        if json_output:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        if refused:
            for item in refused:
                print(
                    "error: refusing to run %s: %s" % (item["command"], item["refused_reason"]),
                    file=sys.stderr,
                )
            return 1
        return 0

    out = sys.stderr if json_output else sys.stdout
    results = []
    failures = []
    accepted_failures = []
    refused_results = []
    for item in selected:
        if item["refused_reason"]:
            print(
                "REFUSED %s: %s (%s)"
                % (item["key"], item["command"], item["refused_reason"]),
                file=out,
                flush=True,
            )
            result = {
                "key": item["key"],
                "command": item["command"],
                "adapter_source": item["adapter_source"],
                "adapter_evidence": item["adapter_evidence"],
                "exit_code": None,
                "duration_s": 0.0,
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
                "status": "refused",
                "error": item["refused_reason"],
            }
            results.append(result)
            refused_results.append(result)
            failures.append("%s refused: %s" % (item["key"], item["refused_reason"]))
            continue
        raw = run_command(item["command"], repo_path, timeout, stream=out)
        result = {
            "key": item["key"],
            "command": item["command"],
            "adapter_source": item["adapter_source"],
            "adapter_evidence": item["adapter_evidence"],
            "exit_code": raw["exit_code"],
            "duration_s": raw["duration_s"],
            "stdout_tail": raw["stdout_tail"],
            "stderr_tail": raw["stderr_tail"],
            "timed_out": raw["timed_out"],
            "status": raw["status"],
            "error": raw["error"],
            "baseline_accepted": False,
            "baseline_entry": None,
        }
        if result["status"] != "pass":
            combined = "\n".join(
                (result["stdout_tail"], result["stderr_tail"])
            )
            for file_entry in baselines["file_entries"]:
                matched = next(
                    (entry for entry in file_entry["entries"] if entry in combined), None
                )
                if matched is not None:
                    result["status"] = "baseline_accepted"
                    result["baseline_accepted"] = True
                    result["baseline_entry"] = {
                        "name": file_entry["name"],
                        "path": file_entry["path"],
                        "entry": matched,
                    }
                    accepted_failures.append(
                        "%s: %s (baseline %s)" % (item["key"], matched, file_entry["name"])
                    )
                    print(
                        "  [baseline] accepted known failure: %s" % matched,
                        file=out,
                        flush=True,
                    )
                    break
        if result["status"] in ("fail", "timeout"):
            failures.append("%s: %s" % (item["key"], result["status"]))
        results.append(result)

    duration = round(time.monotonic() - started, 2)
    result_name = "pass" if not failures else "fail"
    finished_at = _now()
    payload = {
        "schema_version": "1",
        "tool": "verify.py",
        "dry_run": False,
        "result": result_name,
        "scope": scope,
        "only": only_keys,
        "adapter": adapter_path,
        "repo": str(repo_path),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_s": duration,
        "timeout_s": timeout,
        "commands": results,
        "failures": failures,
        "baseline": {
            "files": baselines["file_entries"],
            "prose": [
                {"name": entry["name"], "value": entry["value"]}
                for entry in baselines["prose_entries"]
            ],
            "commands": [
                {"name": entry["name"], "value": entry["value"]}
                for entry in baselines["command_entries"]
            ],
            "accepted_failures": accepted_failures,
        },
        "warnings": warnings,
    }
    evidence_paths = _write_evidence(evidence_dir, payload, results)
    payload["evidence"] = evidence_paths

    print("", file=out)
    print("verify: %s" % ("PASS" if result_name == "pass" else "FAIL"), file=out)
    passed = len([result for result in results if result["status"] == "pass"])
    failed = len([result for result in results if result["status"] in ("fail", "timeout")])
    if accepted_failures:
        print("  baseline-accepted known failures: %d" % len(accepted_failures), file=out)
    if refused_results:
        print("  refused commands: %d" % len(refused_results), file=out)
    print(
        "  %d passed, %d failed, %d refused, %d total in %ss"
        % (passed, failed, len(refused_results), len(results), duration),
        file=out,
    )
    if failures:
        for failure in failures:
            print("  FAIL %s" % failure, file=out)
    for warning in warnings:
        print("  warn: %s" % warning, file=out)
    print("evidence: %s" % evidence_paths["markdown"], file=out)
    print("          %s" % evidence_paths["json"], file=out)
    if json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if result_name == "pass" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="verify.py",
        description=(
            "Run an adapter's verify.* commands, print every command before running it, and "
            "write evidence.md/evidence.json. Refuses deploy, release, publish, merge, push, "
            "destroy and migration commands. Read-only by default; --dry-run executes nothing."
        ),
        epilog=(
            "Scopes: changed = lint, typecheck, test_fast (falls back to test); "
            "all = lint, typecheck, build, test_full (falls back to test), e2e, uat. "
            "Exit codes: 0 = pass, 1 = fail/refusal, 2 = bad usage. "
            "Example: verify.py --adapter .aiek/adapter.md --scope changed --json"
        ),
    )
    parser.add_argument(
        "--adapter",
        metavar="PATH",
        help="adapter.md file (or directory); default <repo>/.aiek/adapter.md",
    )
    parser.add_argument("--repo", metavar="PATH", help="project root (default: from adapter)")
    parser.add_argument(
        "--scope",
        choices=("changed", "all"),
        default="changed",
        help="changed = fast checks (default); all = full gate",
    )
    parser.add_argument(
        "--only",
        metavar="KEYS",
        help="comma-separated verify.* keys to run, e.g. test,lint,typecheck",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the machine-readable evidence JSON"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected commands and run nothing (writes no evidence)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        metavar="N",
        help="per-command timeout in seconds (default: 600)",
    )
    parser.add_argument(
        "--evidence-dir",
        metavar="PATH",
        help="where to write evidence.md/evidence.json (default: <repo>/.aiek/evidence)",
    )
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be a positive number of seconds")
    return verify(
        adapter=args.adapter,
        repo=args.repo,
        scope=args.scope,
        only=args.only,
        json_output=args.json,
        dry_run=args.dry_run,
        timeout=args.timeout,
        evidence_dir=args.evidence_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
