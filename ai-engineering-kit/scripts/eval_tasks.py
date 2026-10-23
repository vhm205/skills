#!/usr/bin/env python3
"""Behaviour evaluation for the AI Engineering Kit.

Runs the fixtures in ``evals/tasks/*.md`` against an agent harness in a throw-away
scratch project (with the kit installed through ``scripts/install.sh``) and checks
concrete assertions: lane statement, artifacts created, evidence tables, BLOCKED
questions, ``file:line`` findings, decision/rollback and combined verification.

    python3 scripts/eval_tasks.py --mock                          # offline, CI-safe
    python3 scripts/eval_tasks.py --harness dsh                   # one real run/scenario
    python3 scripts/eval_tasks.py --harness dsh --scenario small-fix --scenario vague-ticket
    python3 scripts/eval_tasks.py --harness dsh --both --benchmark evals/results/benchmark.json

``--mock`` is a deterministic responder: it returns the fixture's synthetic
``Mock response`` (and applies its ``Mock changes``), so CI exercises the fixture
parser, installer, assertion engine and reporting without a model. Mock output is
labelled ``synthetic: true`` in every report and is NOT evidence of agent behaviour;
the real harness is. Real harness failures are recorded, never converted into passes.

Exit codes: 0 = pass rate >= threshold and no critical failure, 1 = below
threshold or a critical assertion failed, 2 = configuration/harness error.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_KIT_ROOT = SCRIPT_DIR.parent
DEFAULT_THRESHOLD = 0.80
DEFAULT_TIMEOUT = 900
SCHEMA = "aiek-behavior-eval/1"
SNAPSHOT_EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", ".worktrees", ".pytest_cache",
                          ".mypy_cache", ".ruff_cache", ".venv", "venv", ".isolated-agents-home"}

# Reuse the harness adapters and helpers from the trigger eval (same directory).
sys.path.insert(0, str(SCRIPT_DIR))
import eval_trigger  # noqa: E402  (local module, same directory)


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Fixture parsing
# --------------------------------------------------------------------------- #

FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)\n```", re.S)
SECTION_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
SUBSECTION_RE = re.compile(r"(?m)^###\s+(.+?)\s*$")


def _fence_ranges(text: str) -> list[tuple[int, int]]:
    """Character ranges covered by ``` fences, so headings inside code blocks are ignored."""
    ranges: list[tuple[int, int]] = []
    open_at: int | None = None
    for match in re.finditer(r"(?m)^[ \t]*```[^\n]*$", text):
        if open_at is None:
            open_at = match.start()
        else:
            ranges.append((open_at, match.end()))
            open_at = None
    if open_at is not None:
        ranges.append((open_at, len(text)))
    return ranges


def _heading_matches(regex: re.Pattern, text: str) -> list[re.Match]:
    fences = _fence_ranges(text)

    def inside_fence(position: int) -> bool:
        return any(start <= position < end for start, end in fences)

    return [match for match in regex.finditer(text) if not inside_fence(match.start())]


class FixtureError(RuntimeError):
    pass


def _fenced(body: str, *, what: str) -> str:
    match = FENCE_RE.search(body)
    if not match:
        raise FixtureError(f"missing {what} code fence")
    return match.group(1).strip("\n")


def _sub_blocks(body: str) -> list[tuple[str, str]]:
    """Return (relative path, content) pairs from ``### path`` + fenced blocks."""
    blocks: list[tuple[str, str]] = []
    matches = _heading_matches(SUBSECTION_RE, body)
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = _fenced(body[start:end], what=f"content for {match.group(1).strip()}")
        blocks.append((match.group(1).strip(), content))
    return blocks


def parse_fixture(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    sections = _heading_matches(SECTION_RE, text)
    preamble = text[: sections[0].start()] if sections else text
    meta: dict = {}
    for line in preamble.splitlines():
        match = re.match(r"^-\s+([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$", line)
        if match:
            key, value = match.group(1), match.group(2)
            if value.lower() in ("true", "false"):
                meta[key] = value.lower() == "true"
            elif value.isdigit():
                meta[key] = int(value)
            else:
                meta[key] = value
    if "id" not in meta:
        raise FixtureError(f"{path}: missing '- id:' metadata")
    sections_by_title: dict[str, str] = {}
    for index, match in enumerate(sections):
        start = match.end()
        end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
        sections_by_title[match.group(1).strip().lower()] = text[start:end]
    fixture = {
        "id": meta["id"],
        "title": meta.get("title", meta["id"]),
        "critical": bool(meta.get("critical", False)),
        "timeout_s": int(meta.get("timeout_s", DEFAULT_TIMEOUT)),
        "lane": meta.get("lane", "UNKNOWN"),
        "file": str(path),
        "prompt": _fenced(sections_by_title.get("prompt", ""), what="prompt"),
        "setup": _sub_blocks(sections_by_title.get("setup", "")),
        "assertions": _parse_assertions(sections_by_title.get("assertions", ""), path),
        "mock_changes": _sub_blocks(sections_by_title.get("mock changes", "")),
        "mock_response": _fenced_optional(sections_by_title.get("mock response", "")),
        "mock_response_without_kit": _fenced_optional(sections_by_title.get("mock response without kit", "")),
    }
    if not fixture["mock_response"]:
        raise FixtureError(f"{path}: missing '## Mock response'")
    if not fixture["mock_response_without_kit"]:
        fixture["mock_response_without_kit"] = fixture["mock_response"]
    return fixture


def _fenced_optional(body: str) -> str:
    match = FENCE_RE.search(body)
    return match.group(1).strip("\n") if match else ""


def _parse_assertions(body: str, path: Path) -> list[dict]:
    if not body.strip():
        raise FixtureError(f"{path}: missing '## Assertions' section")
    raw = _fenced(body, what="assertions JSON")
    try:
        assertions = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"{path}: assertions are not valid JSON: {exc}") from exc
    if not isinstance(assertions, list) or not assertions:
        raise FixtureError(f"{path}: assertions must be a non-empty list")
    for assertion in assertions:
        if "id" not in assertion or "kind" not in assertion or "description" not in assertion:
            raise FixtureError(f"{path}: assertion needs id/kind/description: {assertion}")
        assertion.setdefault("critical", False)
    return assertions


def load_fixtures(tasks_dir: Path, only: list[str] | None = None) -> list[dict]:
    if not tasks_dir.is_dir():
        raise FixtureError(f"tasks directory not found: {tasks_dir}")
    fixtures = [parse_fixture(path) for path in sorted(tasks_dir.glob("*.md"))]
    if only:
        wanted = {item.strip() for item in only}
        fixtures = [fixture for fixture in fixtures if fixture["id"] in wanted]
        unknown = wanted - {fixture["id"] for fixture in fixtures}
        if unknown:
            raise FixtureError(f"unknown scenario id(s): {', '.join(sorted(unknown))}")
    if not fixtures:
        raise FixtureError("no fixtures selected")
    return fixtures


# --------------------------------------------------------------------------- #
# Scratch project
# --------------------------------------------------------------------------- #

def write_blocks(root: Path, blocks: list[tuple[str, str]]) -> None:
    for relative, content in blocks:
        target = (root / relative).resolve()
        if not str(target).startswith(str(root.resolve()) + os.sep):
            raise FixtureError(f"fixture path escapes the scratch project: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8")


def git_init_commit(root: Path) -> str | None:
    git = shutil.which("git")
    if not git:
        return "git not found; scratch project is not a repository"
    commands = [
        [git, "init", "-q"],
        [git, "add", "-A"],
        [git, "-c", "user.email=eval@example.com", "-c", "user.name=eval", "commit", "-q", "-m", "fixture"],
    ]
    for command in commands:
        rc, out, err, _, _ = eval_trigger.run_process(command, cwd=root, timeout=60)
        if rc != 0:
            return f"{' '.join(command[:2])} failed: {(err or out).strip()[-300:]}"
    return None


def file_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in SNAPSHOT_EXCLUDED_DIRS for part in relative_parts):
            continue
        try:
            snapshot[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return snapshot


def diff_snapshots(before: dict[str, str], after: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    created = sorted(path for path in after if path not in before)
    changed = sorted(path for path in after if path in before and after[path] != before[path])
    removed = sorted(path for path in before if path not in after)
    return created, changed, removed


def install_kit(kit_root: Path, scratch: Path) -> dict:
    install_script = kit_root / "scripts" / "install.sh"
    rc, out, err, duration, _ = eval_trigger.run_process(
        ["bash", str(install_script), str(scratch)], cwd=kit_root, timeout=180, env=dict(os.environ)
    )
    return {
        "command": ["bash", str(install_script), "<scratch>"],
        "returncode": rc,
        "duration_s": round(duration, 2),
        "ok": rc == 0,
        "stderr_excerpt": (err or "")[-500:],
    }


# --------------------------------------------------------------------------- #
# Mock harness for behaviour eval
# --------------------------------------------------------------------------- #

class MockBehaviorHarness(eval_trigger.Harness):
    """Returns the fixture's synthetic response instead of calling a model."""

    name = "mock"

    def __init__(self, fixture: dict, with_skill: bool) -> None:
        self.fixture = fixture
        self.with_skill = with_skill

    def run(self, prompt: str, cwd: Path, env: dict[str, str] | None, timeout: float) -> eval_trigger.HarnessResult:
        started = time.monotonic()
        text = self.fixture["mock_response"] if self.with_skill else self.fixture["mock_response_without_kit"]
        return eval_trigger.HarnessResult(
            skills_used=[],
            source="heuristic",
            text=text,
            duration_s=time.monotonic() - started,
            usage={"totalTokens": 0, "outputTokens": 0},
            command=["mock-behaviour-responder"],
        )

    def probe(self, cwd: Path, env: dict[str, str] | None, timeout: float) -> dict:
        return {"harness": "mock", "ok": True, "detail": "synthetic fixture responder (offline)"}


# --------------------------------------------------------------------------- #
# Assertions
# --------------------------------------------------------------------------- #

def _regex(pattern: str, flags: int) -> re.Pattern:
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise FixtureError(f"invalid assertion regex {pattern!r}: {exc}") from exc


def _flags(assertion: dict) -> int:
    raw = str(assertion.get("flags", "im")).lower()
    flags = 0
    if "i" in raw:
        flags |= re.I
    if "m" in raw:
        flags |= re.M
    if "s" in raw:
        flags |= re.S
    return flags


def _glob_match(glob: str, paths: list[str]) -> list[str]:
    # fnmatch-style globs relative to the scratch root; '*' crosses directories.
    pattern = glob.replace("\\", "/")
    return [path for path in paths if fnmatch.fnmatchcase(path, pattern) or path == pattern]


def evaluate_assertion(assertion: dict, output: str, root: Path,
                       created: list[str], changed: list[str], removed: list[str]) -> dict:
    kind = assertion["kind"]
    result = {
        "id": assertion["id"],
        "description": assertion["description"],
        "kind": kind,
        "critical": bool(assertion.get("critical")),
        "passed": False,
        "detail": "",
    }
    try:
        if kind == "output_regex":
            match = _regex(assertion["pattern"], _flags(assertion)).search(output)
            result["passed"] = bool(match)
            result["detail"] = f"matched {match.group(0)[:120]!r}" if match else "pattern not found in output"
        elif kind == "output_not_regex":
            match = _regex(assertion["pattern"], _flags(assertion)).search(output)
            result["passed"] = not match
            result["detail"] = "pattern absent from output" if not match else f"forbidden match {match.group(0)[:120]!r}"
        elif kind == "output_order":
            before = _regex(assertion["before"], _flags(assertion)).search(output)
            after = _regex(assertion["after"], _flags(assertion)).search(output)
            if not before or not after:
                result["detail"] = f"missing pattern ({'before' if not before else 'after'})"
            else:
                result["passed"] = before.start() < after.start()
                result["detail"] = f"order {before.start()} < {after.start()}" if result["passed"] else "DONE appears before evidence"
        elif kind == "min_questions":
            minimum = int(assertion.get("min", 1))
            count = output.count("?")
            result["passed"] = count >= minimum
            result["detail"] = f"{count} question mark(s), need >= {minimum}"
        elif kind == "file_contains":
            path = root / assertion["path"]
            if not path.is_file():
                result["detail"] = f"file missing: {assertion['path']}"
            else:
                match = _regex(assertion["pattern"], _flags(assertion)).search(path.read_text(encoding="utf-8", errors="replace"))
                result["passed"] = bool(match)
                result["detail"] = f"matched {match.group(0)[:120]!r}" if match else "pattern not found in file"
        elif kind == "file_not_contains":
            path = root / assertion["path"]
            if not path.is_file():
                result["detail"] = f"file missing: {assertion['path']}"
            else:
                match = _regex(assertion["pattern"], _flags(assertion)).search(path.read_text(encoding="utf-8", errors="replace"))
                result["passed"] = not match
                result["detail"] = "forbidden pattern absent" if not match else f"forbidden match {match.group(0)[:120]!r}"
        elif kind == "file_exists":
            path = root / assertion["path"]
            result["passed"] = path.is_file()
            result["detail"] = "exists" if path.is_file() else f"missing {assertion['path']}"
        elif kind == "glob_exists":
            matches = _glob_match(assertion["glob"], sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()))
            result["passed"] = bool(matches)
            result["detail"] = f"{len(matches)} match(es): {matches[:3]}" if matches else "no files matched"
        elif kind == "changed_glob":
            matches = _glob_match(assertion["glob"], created + changed)
            result["passed"] = bool(matches)
            result["detail"] = f"changed: {matches[:5]}" if matches else "no matching file changed/created"
        elif kind == "unchanged_glob":
            matches = _glob_match(assertion["glob"], created + changed + removed)
            result["passed"] = not matches
            result["detail"] = "unchanged" if not matches else f"unexpected changes: {matches[:5]}"
        elif kind == "new_glob_absent":
            matches = _glob_match(assertion["glob"], created)
            result["passed"] = not matches
            result["detail"] = "no new files" if not matches else f"unexpected new files: {matches[:5]}"
        else:
            raise FixtureError(f"unknown assertion kind {kind!r} in {assertion['id']}")
    except (FixtureError, OSError) as exc:
        result["detail"] = f"assertion error: {exc}"
        raise
    return result


# --------------------------------------------------------------------------- #
# Harness resolution
# --------------------------------------------------------------------------- #

def resolve_harness(name: str) -> tuple[object, list[dict]]:
    probes: list[dict] = []
    if name == "mock":
        return None, probes
    factories = {"dsh": eval_trigger.DshHarness, "claude": eval_trigger.ClaudeHarness, "codex": eval_trigger.CodexHarness}
    candidates = ["dsh", "claude", "codex"] if name == "auto" else [name]
    for candidate in candidates:
        try:
            return factories[candidate](), [{"harness": candidate, "ok": True, "detail": "binary found"}]
        except eval_trigger.HarnessError as exc:
            probes.append({"harness": candidate, "ok": False, "detail": str(exc)})
    return None, probes


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def run_scenario(fixture: dict, *, harness, harness_name: str, with_skill: bool, kit_root: Path,
                 timeout: float, dry_run: bool, keep_scratch: bool) -> dict:
    scratch = Path(tempfile.mkdtemp(prefix=f"aiek-behavior-{fixture['id']}-"))
    report: dict = {
        "id": fixture["id"],
        "title": fixture["title"],
        "lane": fixture["lane"],
        "critical": fixture["critical"],
        "with_skill": with_skill,
        "synthetic": harness_name == "mock",
        "passed": False,
        "critical_failed": False,
        "assertions": [],
        "error": None,
        "duration_s": 0.0,
        "usage": {},
        "changed_files": [],
        "created_files": [],
        "removed_files": [],
        "install": None,
        "output_excerpt": "",
        "scratch": str(scratch) if keep_scratch else None,
    }
    if dry_run:
        report["planned"] = True
        report["passed"] = True  # dry-run: nothing executed, nothing to score
        report["assertion_count"] = len(fixture["assertions"])
        report["setup_files"] = [path for path, _ in fixture["setup"]]
        report["critical_assertions"] = [a["id"] for a in fixture["assertions"] if a.get("critical")]
        shutil.rmtree(scratch, ignore_errors=True)
        return report
    try:
        write_blocks(scratch, fixture["setup"])
        commit_error = git_init_commit(scratch)
        if commit_error:
            report["error"] = commit_error
            return report
        if with_skill and harness_name != "mock":
            report["install"] = install_kit(kit_root, scratch)
        elif with_skill and harness_name == "mock":
            report["install"] = {"ok": None, "note": "mock mode does not install the kit; synthetic response used"}
        before = file_snapshot(scratch)
        env = dict(os.environ)
        isolated_agents = scratch / ".isolated-agents-home"
        isolated_agents.mkdir(exist_ok=True)
        env["DSH_AGENTS_HOME"] = str(isolated_agents)
        if harness_name == "mock":
            if with_skill:
                write_blocks(scratch, fixture["mock_changes"])
            result = MockBehaviorHarness(fixture, with_skill).run("", scratch, env, timeout)
        else:
            result = harness.run(fixture["prompt"], scratch, env, timeout)
        report["duration_s"] = round(result.duration_s, 2)
        report["usage"] = result.usage or {}
        report["output_excerpt"] = (result.text or "")[:2000]
        report["error"] = result.error
        after = file_snapshot(scratch)
        created, changed, removed = diff_snapshots(before, after)
        report["created_files"] = created
        report["changed_files"] = changed
        report["removed_files"] = removed
        if result.error:
            report["assertions"] = [
                {"id": a["id"], "description": a["description"], "kind": a["kind"],
                 "critical": bool(a.get("critical")), "passed": False, "detail": "harness error"}
                for a in fixture["assertions"]
            ]
            report["critical_failed"] = any(a.get("critical") for a in fixture["assertions"])
            return report
        results = [
            evaluate_assertion(assertion, result.text or "", scratch, created, changed, removed)
            for assertion in fixture["assertions"]
        ]
        report["assertions"] = results
        report["critical_failed"] = any(row["critical"] and not row["passed"] for row in results)
        report["passed"] = all(row["passed"] for row in results)
        return report
    finally:
        if not keep_scratch:
            shutil.rmtree(scratch, ignore_errors=True)


def run_all(fixtures: list[dict], *, harness_name: str, with_skill: bool, runs: int, kit_root: Path,
            timeout: float, dry_run: bool, keep_scratch: bool, kit_label: str | None) -> dict:
    harness, probes = resolve_harness(harness_name)
    if harness_name != "mock" and harness is None:
        return {
            "schema": SCHEMA,
            "generated_at": utc_now(),
            "kit_root": str(kit_root),
            "kit_label": kit_label,
            "harness": {"requested": harness_name, "resolved": None, "probes": probes},
            "error": "no requested harness is available; run with --mock for the offline path",
            "scenarios": [],
            "summary": {"total": 0, "passed": 0, "pass_rate": 0.0, "critical_failures": 0},
            "limitations": ["harness unavailable: " + json.dumps(probes)],
        }
    resolved_name = "mock" if harness_name == "mock" else harness_name
    # dsh runs via the headless profile; its --json events give us the final text.
    scenario_reports: list[dict] = []
    for fixture in fixtures:
        run_reports = [
            run_scenario(fixture, harness=harness, harness_name=resolved_name, with_skill=with_skill,
                         kit_root=kit_root, timeout=min(timeout, fixture["timeout_s"]),
                         dry_run=dry_run, keep_scratch=keep_scratch)
            for _ in range(1 if resolved_name == "mock" or dry_run else runs)
        ]
        passed_runs = [report for report in run_reports if report["passed"]]
        merged = dict(run_reports[0])
        merged["runs"] = [
            {"passed": report["passed"], "assertions": report["assertions"], "error": report["error"],
             "duration_s": report["duration_s"], "usage": report["usage"]}
            for report in run_reports
        ]
        merged["passed"] = len(passed_runs) >= max(1, (len(run_reports) + 1) // 2)
        merged["critical_failed"] = any(report["critical_failed"] for report in run_reports)
        if len(run_reports) > 1:
            # Majority: report the assertions of a representative run (the first pass,
            # else the first run) and keep every per-run detail in "runs".
            merged["assertions"] = (passed_runs[0] if passed_runs else run_reports[0])["assertions"]
            merged["error"] = next((report["error"] for report in run_reports if report["error"]), None)
        scenario_reports.append(merged)
        status = "PLANNED" if dry_run else ("PASS" if merged["passed"] else "FAIL")
        failed = [row["id"] for row in merged["assertions"] if not row["passed"]]
        eprint(f"  [{fixture['id']}] {status} ({merged['duration_s']:.1f}s)"
               + (f" failed: {', '.join(failed)}" if failed else "")
               + (f" error: {merged['error']}" if merged["error"] else ""))
    total = len(scenario_reports)
    passed = sum(1 for report in scenario_reports if report["passed"])
    critical_failures = [report["id"] for report in scenario_reports if report["critical_failed"]]
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "critical_failures": len(critical_failures),
        "critical_failure_scenarios": critical_failures,
        "avg_duration_s": round(sum(report["duration_s"] for report in scenario_reports) / total, 2) if total else 0.0,
        "total_tokens": sum(int((report.get("usage") or {}).get("totalTokens") or 0) for report in scenario_reports),
    }
    limitations: list[str] = []
    if resolved_name == "mock":
        limitations.append(
            "Mock mode returns the fixture's synthetic mock response and applies its mock changes. "
            "It validates the fixture parser, installer wiring and assertion engine only; it is NOT "
            "evidence of agent behaviour and must not be quoted as a behaviour pass rate."
        )
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "kit_root": str(kit_root),
        "kit_label": kit_label,
        "harness": {"requested": harness_name, "resolved": resolved_name, "probes": probes},
        "with_skill": with_skill,
        "synthetic": resolved_name == "mock",
        "runs_per_scenario": 1 if resolved_name == "mock" or dry_run else runs,
        "timeout_s": timeout,
        "scenarios": scenario_reports,
        "summary": summary,
        "limitations": limitations,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Behaviour eval for the AI Engineering Kit (7 fixtures in evals/tasks).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  python3 scripts/eval_tasks.py --mock\n"
        "  python3 scripts/eval_tasks.py --harness dsh --scenario small-fix --scenario vague-ticket\n"
        "  python3 scripts/eval_tasks.py --harness dsh --both --benchmark evals/results/benchmark.json\n",
    )
    parser.add_argument("--harness", choices=["auto", "dsh", "claude", "codex", "mock"], default="auto",
                        help="harness to use; auto prefers dsh > claude > codex (default)")
    parser.add_argument("--mock", action="store_true", help="shortcut for --harness mock (offline synthetic fixtures)")
    parser.add_argument("--scenario", action="append", default=None,
                        help="scenario id to run; repeatable or comma-separated (default: all)")
    parser.add_argument("--runs", type=int, default=1, help="runs per scenario for real harnesses (default: 1)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="per-scenario timeout in seconds")
    parser.add_argument("--kit-root", type=Path, default=DEFAULT_KIT_ROOT, help="kit to install into the scratch project")
    parser.add_argument("--kit-label", default=None, help="label for the kit under test")
    parser.add_argument("--tasks-dir", type=Path, default=None, help="fixtures directory (default: <kit-root>/evals/tasks)")
    parser.add_argument("--without-skill", action="store_true", help="run scenarios without installing the kit")
    parser.add_argument("--both", action="store_true", help="run with and without the kit and report the comparison")
    parser.add_argument("--benchmark", type=Path, default=None, help="write a with/without benchmark JSON here")
    parser.add_argument("--fail-below", type=float, default=DEFAULT_THRESHOLD,
                        help=f"pass-rate threshold for exit code (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--dry-run", action="store_true", help="parse fixtures and print the plan; run nothing")
    parser.add_argument("--list", action="store_true", help="list scenario ids and titles")
    parser.add_argument("--json", action="store_true", help="print the machine-readable report to stdout")
    parser.add_argument("--out", type=Path, default=None, help="write the JSON report to this path")
    parser.add_argument("--keep-scratch", action="store_true", help="keep scratch projects and report their paths")
    parser.add_argument("--verbose", "-v", action="store_true", help="per-scenario progress on stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kit_root = args.kit_root.resolve()
    tasks_dir = (args.tasks_dir or (kit_root / "evals" / "tasks")).resolve()
    only: list[str] | None = None
    if args.scenario:
        only = [item.strip() for value in args.scenario for item in value.split(",") if item.strip()]
    try:
        fixtures = load_fixtures(tasks_dir, only)
    except FixtureError as exc:
        eprint(f"error: {exc}")
        return 2
    if args.list:
        for fixture in fixtures:
            print(f"{fixture['id']:<16} {fixture['title']} ({len(fixture['assertions'])} assertions)")
        return 0
    if args.runs < 1:
        eprint("error: --runs must be >= 1")
        return 2
    harness_name = "mock" if args.mock else args.harness
    if args.dry_run:
        mode = "mock"
    else:
        mode = harness_name
    eprint(
        f"behaviour eval: {len(fixtures)} scenario(s) | harness={mode}"
        + (" (synthetic)" if mode == "mock" else "")
        + f" | kit={args.kit_label or kit_root}"
    )
    modes = [False, True] if args.both else [not args.without_skill]
    reports: dict[bool, dict] = {}
    exit_code = 0
    for with_skill in modes:
        label = "with_skill" if with_skill else "without_skill"
        eprint(f"  mode: {label}")
        try:
            report = run_all(
                fixtures,
                harness_name=mode,
                with_skill=with_skill,
                runs=args.runs,
                kit_root=kit_root,
                timeout=args.timeout,
                dry_run=args.dry_run,
                keep_scratch=args.keep_scratch,
                kit_label=args.kit_label,
            )
        except FixtureError as exc:
            eprint(f"error: {exc}")
            return 2
        reports[with_skill] = report
        summary = report["summary"]
        eprint(
            f"  {label}: {summary['passed']}/{summary['total']} passed "
            f"(pass_rate={summary['pass_rate']:.1%}, critical_failures={summary['critical_failures']})"
        )
        if report.get("error"):
            eprint(f"  error: {report['error']}")
            return 2
        if not args.dry_run and not args.both:
            if summary["pass_rate"] < args.fail_below or summary["critical_failures"] > 0:
                exit_code = 1
    if args.both:
        gated = reports[True]["summary"]
        if not args.dry_run and (gated["pass_rate"] < args.fail_below or gated["critical_failures"] > 0):
            exit_code = 1
        with_report = reports[True]
        without_report = reports[False]
        benchmark = {
            "schema": "aiek-behavior-benchmark/1",
            "generated_at": utc_now(),
            "harness": with_report["harness"],
            "kit_label": args.kit_label,
            "synthetic": with_report["synthetic"],
            "with_skill": with_report["summary"],
            "without_skill": without_report["summary"],
            "per_scenario": [
                {
                    "id": with_row["id"],
                    "with_skill_passed": with_row["passed"],
                    "without_skill_passed": without_row["passed"],
                    "with_skill_duration_s": with_row["duration_s"],
                    "without_skill_duration_s": without_row["duration_s"],
                    "with_skill_tokens": int((with_row.get("usage") or {}).get("totalTokens") or 0),
                    "without_skill_tokens": int((without_row.get("usage") or {}).get("totalTokens") or 0),
                }
                for with_row, without_row in zip(with_report["scenarios"], without_report["scenarios"])
            ],
            "limitations": with_report["limitations"] + without_report["limitations"],
        }
        if args.benchmark:
            args.benchmark.parent.mkdir(parents=True, exist_ok=True)
            args.benchmark.write_text(json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            eprint(f"  benchmark written: {args.benchmark}")
        payload = benchmark
    else:
        payload = reports[modes[0]]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        eprint(f"  report written: {args.out}")
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    if args.dry_run:
        eprint("dry-run: fixtures parsed, scenarios planned, nothing executed")
        return 0
    if exit_code:
        summary = reports[modes[-1]]["summary"]
        eprint(f"FAIL: pass_rate={summary['pass_rate']:.1%} (threshold {args.fail_below:.0%}) "
               f"or critical failure ({summary['critical_failures']})")
        return 1
    eprint(f"PASS: pass_rate={reports[modes[-1]]['summary']['pass_rate']:.1%} "
           f">= {args.fail_below:.0%} with no critical failure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
