#!/usr/bin/env python3
"""Tests for the installed AI Engineering Kit helper scripts.

Covers ``_adapter_yaml.py``, ``resolve_adapter.py``, ``verify.py``, ``worktree.py``,
``traceability.py`` and the Lead-owned ``check_skills.py`` contract. Uses only temporary
directories and fixture adapters; needs git on PATH for the worktree tests.

Run with any Python 3.9+: ``python3 scripts/test_scripts.py -v``
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SCRIPTS = KIT / "scripts"
PYTHON = sys.executable or "python3"
RESOLVE = SCRIPTS / "resolve_adapter.py"
VERIFY = SCRIPTS / "verify.py"
WORKTREE = SCRIPTS / "worktree.py"
TRACEABILITY = SCRIPTS / "traceability.py"
CHECK_SKILLS = SCRIPTS / "check_skills.py"
GIT = shutil.which("git")
ADAPTER_HEADER = "---\nadapter: test-project\n"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import _adapter_yaml  # noqa: E402


def run(script, *arguments, cwd=None):
    return subprocess.run(
        [PYTHON, str(script)] + [str(argument) for argument in arguments],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def write_adapter(root, body, prose=""):
    aiek = Path(root) / ".aiek"
    aiek.mkdir(parents=True, exist_ok=True)
    (aiek / "adapter.md").write_text(ADAPTER_HEADER + body.strip() + "\n---\n" + prose)
    return aiek / "adapter.md"


def snapshot(root):
    root = Path(root)
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def git_ok(*arguments, cwd):
    result = subprocess.run(
        ["git", "-C", str(cwd)] + list(arguments), capture_output=True, text=True
    )
    if result.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(arguments), result.stderr))
    return result.stdout.strip()


class ScriptTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aiek-scripts-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()

    def assert_rc(self, result, expected):
        self.assertEqual(
            result.returncode,
            expected,
            "expected exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
            % (expected, result.returncode, result.stdout, result.stderr),
        )


# --------------------------------------------------------------------------------------
# _adapter_yaml.py
# --------------------------------------------------------------------------------------


class FrontmatterTests(unittest.TestCase):
    def test_nested_maps_lists_quotes_null_bool(self):
        text = (
            "---\n"
            'adapter: "quoted: project"   # inline comment\n'
            "default_branch: auto\n"
            "verify:\n"
            "  setup: pnpm install\n"
            '  test: "pnpm test -- --reporter=\'dot\'"\n'
            "  e2e: null\n"
            "  run: ~\n"
            "tdd: true\n"
            "optional: false\n"
            "risk_areas:\n"
            '  - "src/auth/**"\n'
            "  - migrations/**\n"
            "empty_list: []\n"
            "inline_list: [a, \"b c\", 3]\n"
            "repos:\n"
            "  be:\n"
            "    dir: server\n"
            "    verify:\n"
            "      test: go test ./...\n"
            "  fe:\n"
            "    dir: web\n"
            "records:\n"
            "  - name: first\n"
            "    glob: src/a/**\n"
            "  - name: second\n"
            "---\n"
            "# prose\n"
        )
        data, prose = _adapter_yaml.parse_frontmatter(text, "fixture.md")
        self.assertEqual(data["adapter"], "quoted: project")
        self.assertEqual(
            data["verify"]["test"], "pnpm test -- --reporter='dot'"
        )
        self.assertIsNone(data["verify"]["e2e"])
        self.assertIsNone(data["verify"]["run"])
        self.assertIs(data["tdd"], True)
        self.assertIs(data["optional"], False)
        self.assertEqual(data["risk_areas"], ["src/auth/**", "migrations/**"])
        self.assertEqual(data["empty_list"], [])
        self.assertEqual(data["inline_list"], ["a", "b c", "3"])
        self.assertEqual(data["repos"]["be"]["verify"]["test"], "go test ./...")
        self.assertEqual(data["repos"]["fe"]["dir"], "web")
        self.assertEqual(
            data["records"],
            [{"name": "first", "glob": "src/a/**"}, {"name": "second"}],
        )
        self.assertEqual(prose, "# prose")

    def test_duplicate_key_reports_line(self):
        with self.assertRaises(_adapter_yaml.FrontmatterError) as context:
            _adapter_yaml.parse_frontmatter(
                "---\nverify:\n  test: a\n  test: b\n---\n", "dup.md"
            )
        self.assertIn("dup.md:4:", str(context.exception))
        self.assertIn("duplicate key 'test'", str(context.exception))

    def test_indentation_errors_report_line(self):
        with self.assertRaises(_adapter_yaml.FrontmatterError) as context:
            _adapter_yaml.parse_frontmatter(
                "---\nverify:\n  test: a\n   lint: b\n---\n", "indent.md"
            )
        self.assertIn("indent.md:4:", str(context.exception))
        self.assertIn("indentation", str(context.exception))

    def test_tabs_rejected(self):
        with self.assertRaises(_adapter_yaml.FrontmatterError) as context:
            _adapter_yaml.parse_frontmatter("---\n\ttest: a\n---\n", "tab.md")
        self.assertIn("tab", str(context.exception).lower())

    def test_unsupported_block_scalar(self):
        with self.assertRaises(_adapter_yaml.FrontmatterError) as context:
            _adapter_yaml.parse_frontmatter("---\ntest: |\n  a\n---\n", "block.md")
        self.assertIn("block scalar", str(context.exception))

    def test_unterminated_frontmatter_and_quotes(self):
        with self.assertRaises(_adapter_yaml.FrontmatterError):
            _adapter_yaml.parse_frontmatter("---\ntest: a\n", "open.md")
        with self.assertRaises(_adapter_yaml.FrontmatterError):
            _adapter_yaml.parse_frontmatter("---\ntest: \"a\n---\n", "quote.md")
        with self.assertRaises(_adapter_yaml.FrontmatterError):
            _adapter_yaml.parse_frontmatter("no frontmatter\n", "none.md")

    def test_load_adapter_missing_file(self):
        with self.assertRaises(_adapter_yaml.FrontmatterError) as context:
            _adapter_yaml.load_adapter("/nonexistent/adapter.md")
        self.assertIn("not found", str(context.exception))

    def test_get_dotted(self):
        data = {"verify": {"test_fast": "x"}}
        self.assertEqual(_adapter_yaml.get(data, "verify.test_fast"), "x")
        self.assertIsNone(_adapter_yaml.get(data, "verify.test.full"))


# --------------------------------------------------------------------------------------
# resolve_adapter.py
# --------------------------------------------------------------------------------------


class ResolveAdapterTests(ScriptTestCase):
    def test_explicit_values_and_json_sources(self):
        write_adapter(
            self.root,
            """
verify:
  setup: pnpm install
  test: pnpm test
  e2e: null
planning:
  mode: external
  plan_path: docs/plan.md
baselines:
  - name: unit
    kind: prose
    value: "2 checkout tests fail on main"
worktree_name_pattern: "{repo}-wt-{slug}"
branch_pattern: "{type}/{ticket}-{slug}"
""",
        )
        result = run(RESOLVE, "--repo", self.root, "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        verify = payload["adapter"]["verify"]
        self.assertEqual(verify["setup"]["value"], "pnpm install")
        self.assertEqual(verify["setup"]["source"], "adapter")
        self.assertEqual(verify["test"]["value"], "pnpm test")
        self.assertEqual(verify["test"]["source"], "adapter")
        self.assertIsNone(verify["e2e"]["value"])
        self.assertEqual(verify["e2e"]["source"], "adapter")
        self.assertEqual(payload["adapter"]["planning"]["value"]["mode"], "external")
        self.assertEqual(payload["adapter"]["baselines"]["value"][0]["kind"], "prose")
        self.assertEqual(
            payload["adapter"]["worktree_name_pattern"]["value"], "{repo}-wt-{slug}"
        )
        # discovery fills the rest from an empty repo: unavailable, not invented
        self.assertEqual(verify["lint"]["source"], "unavailable")
        self.assertIsNone(verify["lint"]["value"])

    def test_auto_values_are_discovered_from_docs_first(self):
        write_adapter(self.root, "\nverify:\n  test: auto\n  lint: auto\n")
        (self.root / "AGENTS.md").write_text(
            "# AGENTS\n\n## Testing\n\n```bash\npython3 -m pytest -q\n```\n\n"
            "## Linting\n\nRun `ruff check .` before committing.\n"
        )
        makefile = self.root / "Makefile"
        makefile.write_text("test:\n\tpython3 -m pytest\n\nlint:\n\truff check .\n")
        result = run(RESOLVE, "--repo", self.root, "--json")
        self.assert_rc(result, 0)
        verify = json.loads(result.stdout)["adapter"]["verify"]
        self.assertEqual(verify["test"]["value"], "python3 -m pytest -q")
        self.assertEqual(verify["test"]["source"], "discovered")
        self.assertIn("AGENTS.md", verify["test"]["evidence"])
        # docs win over the task runner, per command-discovery.md order
        self.assertEqual(verify["lint"]["value"], "ruff check .")
        self.assertIn("AGENTS.md", verify["lint"]["evidence"])

    def test_task_runner_before_package_json(self):
        write_adapter(self.root, "\nverify:\n  test: auto\n")
        (self.root / "Makefile").write_text("test:\n\tpython3 -m pytest\n")
        (self.root / "package.json").write_text(
            json.dumps({"scripts": {"test": "vitest run"}})
        )
        (self.root / "pnpm-lock.yaml").write_text("")
        result = run(RESOLVE, "--repo", self.root, "--json")
        verify = json.loads(result.stdout)["adapter"]["verify"]
        self.assertEqual(verify["test"]["value"], "make test")
        self.assertIn("Makefile", verify["test"]["evidence"])

    def test_package_manager_detection_and_derivation(self):
        write_adapter(self.root, "\nverify:\n  test: auto\n  e2e: null\n")
        (self.root / "package.json").write_text(
            json.dumps(
                {
                    "scripts": {
                        "test": "vitest run",
                        "test:unit": "vitest run unit",
                        "lint": "eslint .",
                        "typecheck": "tsc --noEmit",
                    }
                }
            )
        )
        (self.root / "pnpm-lock.yaml").write_text("")
        result = run(RESOLVE, "--repo", self.root, "--json")
        self.assert_rc(result, 0)
        verify = json.loads(result.stdout)["adapter"]["verify"]
        self.assertEqual(verify["test"]["value"], "pnpm run test")
        self.assertEqual(verify["test_fast"]["value"], "pnpm run test:unit")
        self.assertEqual(verify["test_full"]["value"], "pnpm run test")
        self.assertEqual(verify["test_full"]["source"], "derived")
        self.assertEqual(verify["lint"]["value"], "pnpm run lint")
        self.assertEqual(verify["typecheck"]["value"], "pnpm run typecheck")

    def test_default_branch_detected_from_origin_head_without_running_git(self):
        write_adapter(self.root, "\ndefault_branch: auto\n")
        refs = self.root / ".git" / "refs" / "remotes" / "origin"
        refs.mkdir(parents=True)
        (refs / "HEAD").write_text("ref: refs/remotes/origin/trunk\n")
        result = run(RESOLVE, "--repo", self.root, "--json")
        branch = json.loads(result.stdout)["adapter"]["default_branch"]
        self.assertEqual(branch["value"], "trunk")
        self.assertEqual(branch["source"], "discovered")

    def test_read_only(self):
        write_adapter(self.root, "\nverify:\n  test: auto\n")
        (self.root / "package.json").write_text(json.dumps({"scripts": {"test": "x"}}))
        before = snapshot(self.root)
        result = run(RESOLVE, "--repo", self.root)
        self.assert_rc(result, 0)
        self.assertEqual(snapshot(self.root), before)

    def test_adapter_only_infers_repo(self):
        write_adapter(self.root, "\nverify:\n  test: echo hi\n")
        result = run(RESOLVE, "--adapter", self.root / ".aiek" / "adapter.md", "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(Path(payload["adapter"]["repo"]), self.root.resolve())

    def test_errors_and_exit_codes(self):
        result = run(RESOLVE, "--adapter", self.root / "nope.md")
        self.assert_rc(result, 1)
        self.assertIn("not found", result.stderr)
        write_adapter(self.root, "\nverify:\n  test: 'unterminated\n")
        result = run(RESOLVE, "--repo", self.root)
        self.assert_rc(result, 1)
        self.assertIn("adapter.md:", result.stderr)
        result = run(RESOLVE, "--bogus")
        self.assert_rc(result, 2)
        result = run(RESOLVE, "--help")
        self.assert_rc(result, 0)
        self.assertIn("--adapter", result.stdout)

    def test_invalid_planning_mode(self):
        write_adapter(self.root, "\nplanning:\n  mode: kanban\n")
        result = run(RESOLVE, "--repo", self.root)
        self.assert_rc(result, 1)
        self.assertIn("planning.mode", result.stderr)

    def test_unknown_verify_key_warns(self):
        write_adapter(self.root, "\nverify:\n  tests: pytest\n")
        result = run(RESOLVE, "--repo", self.root, "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(
            any("unknown verify key 'tests'" in warning for warning in payload["warnings"])
        )


# --------------------------------------------------------------------------------------
# verify.py
# --------------------------------------------------------------------------------------


class VerifyTests(ScriptTestCase):
    def adapter(self, verify_body):
        write_adapter(self.root, "verify:\n" + verify_body + "\n")

    def evidence(self):
        return self.root / ".aiek" / "evidence"

    def test_passing_commands_write_evidence(self):
        self.adapter(
            '  lint: python3 -c "print(\'lint ok\')"\n'
            '  test_fast: python3 -c "print(\'fast ok\')"\n'
        )
        result = run(VERIFY, "--repo", self.root, "--only", "lint,test_fast", "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "pass")
        self.assertEqual([command["status"] for command in payload["commands"]], ["pass", "pass"])
        self.assertTrue((self.evidence() / "evidence.md").is_file())
        evidence = json.loads((self.evidence() / "evidence.json").read_text())
        self.assertEqual(evidence["result"], "pass")
        self.assertIn("lint ok", evidence["commands"][0]["stdout_tail"])

    def test_failing_command_exits_nonzero(self):
        self.adapter('  test: python3 -c "import sys; sys.exit(3)"\n')
        result = run(VERIFY, "--repo", self.root, "--only", "test")
        self.assert_rc(result, 1)
        self.assertIn("FAIL", result.stdout)
        evidence = json.loads((self.evidence() / "evidence.json").read_text())
        self.assertEqual(evidence["result"], "fail")
        self.assertEqual(evidence["commands"][0]["exit_code"], 3)

    def test_dry_run_executes_and_writes_nothing(self):
        self.adapter(
            '  test: python3 -c "open(\'ran.txt\', \'w\').write(\'x\')"\n'
        )
        result = run(VERIFY, "--repo", self.root, "--only", "test", "--dry-run")
        self.assert_rc(result, 0)
        self.assertIn("dry-run", result.stdout)
        self.assertFalse((self.root / "ran.txt").exists())
        self.assertFalse(self.evidence().exists())

    def test_refuses_deploy_style_commands(self):
        self.adapter('  typecheck: npm run deploy\n')
        result = run(VERIFY, "--repo", self.root, "--only", "typecheck")
        self.assert_rc(result, 1)
        self.assertIn("REFUSED", result.stdout)
        self.assertIn("deploy", result.stdout.lower())
        evidence = json.loads((self.evidence() / "evidence.json").read_text())
        self.assertEqual(evidence["commands"][0]["status"], "refused")

    def test_refuses_deploy_check_key_even_with_harmless_command(self):
        self.adapter('  deploy_check: python3 -c "print(1)"\n')
        result = run(VERIFY, "--repo", self.root, "--only", "deploy_check")
        self.assert_rc(result, 1)
        self.assertIn("deployed environment", result.stdout)

    def test_baseline_file_accepts_known_failure(self):
        self.adapter(
            '  test: python3 -c "import sys; print(\'KNOWN-BROKEN\'); sys.exit(1)"\n'
        )
        baseline = self.root / "docs" / "baseline.txt"
        baseline.parent.mkdir()
        baseline.write_text("# known failures\nKNOWN-BROKEN\n")
        write_adapter(
            self.root,
            """
verify:
  test: python3 -c "import sys; print('KNOWN-BROKEN'); sys.exit(1)"
baselines:
  - name: unit
    kind: file
    value: docs/baseline.txt
""",
        )
        result = run(VERIFY, "--repo", self.root, "--only", "test")
        self.assert_rc(result, 0)
        self.assertIn("baseline", result.stdout.lower())
        evidence = json.loads((self.evidence() / "evidence.json").read_text())
        self.assertEqual(evidence["result"], "pass")
        self.assertEqual(len(evidence["baseline"]["accepted_failures"]), 1)

    def test_prose_baseline_does_not_hide_failures(self):
        write_adapter(
            self.root,
            """
verify:
  test: python3 -c "import sys; sys.exit(1)"
baselines:
  - name: e2e
    kind: prose
    value: "3 checkout tests fail on main since 2026-10-01"
""",
        )
        result = run(VERIFY, "--repo", self.root, "--only", "test")
        self.assert_rc(result, 1)
        self.assertIn("prose", result.stdout.lower())

    def test_timeout_kills_command(self):
        self.adapter(
            '  test_fast: python3 -c "import time; time.sleep(10)"\n'
        )
        result = run(
            VERIFY, "--repo", self.root, "--only", "test_fast", "--timeout", "1", "--json"
        )
        self.assert_rc(result, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["commands"][0]["timed_out"])
        self.assertEqual(payload["commands"][0]["status"], "timeout")

    def test_selection_errors(self):
        self.adapter('  lint: python3 -c "print(1)"\n  e2e: null\n')
        result = run(VERIFY, "--repo", self.root, "--only", "e2e")
        self.assert_rc(result, 1)
        self.assertIn("not available", result.stderr)
        result = run(VERIFY, "--repo", self.root, "--only", "bogus")
        self.assert_rc(result, 2)
        result = run(VERIFY, "--repo", self.root, "--scope", "bogus")
        self.assert_rc(result, 2)
        result = run(VERIFY, "--help")
        self.assert_rc(result, 0)
        self.assertIn("--evidence-dir", result.stdout)

    def test_scope_changed_uses_fast_then_full(self):
        write_adapter(
            self.root,
            """
verify:
  lint: python3 -c "print('lint')"
  typecheck: python3 -c "print('types')"
  test: python3 -c "print('full')"
""",
        )
        result = run(VERIFY, "--repo", self.root, "--scope", "changed", "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [command["key"] for command in payload["commands"]],
            ["lint", "typecheck", "test_fast"],
        )
        result = run(VERIFY, "--repo", self.root, "--scope", "all", "--dry-run", "--json")
        self.assert_rc(result, 0)
        all_payload = json.loads(result.stdout)
        self.assertEqual(
            [command["key"] for command in all_payload["commands"]],
            ["lint", "typecheck", "test_full"],
        )

    def test_custom_evidence_dir(self):
        self.adapter('  lint: python3 -c "print(1)"\n')
        evidence = self.root / "artifacts"
        result = run(
            VERIFY,
            "--repo",
            self.root,
            "--only",
            "lint",
            "--evidence-dir",
            evidence,
        )
        self.assert_rc(result, 0)
        self.assertTrue((evidence / "evidence.md").is_file())
        self.assertTrue((evidence / "evidence.json").is_file())


# --------------------------------------------------------------------------------------
# worktree.py
# --------------------------------------------------------------------------------------


@unittest.skipUnless(GIT, "git is required for worktree tests")
class WorktreeTests(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.repo = self.root
        git_ok("init", "-q", cwd=self.repo)
        git_ok("config", "user.email", "test@example.com", cwd=self.repo)
        git_ok("config", "user.name", "Test", cwd=self.repo)
        (self.repo / "README.md").write_text("hello\n")
        (self.repo / ".gitignore").write_text(".worktrees/\n")
        (self.repo / ".env.example").write_text("TOKEN=\n")
        git_ok("add", "-A", cwd=self.repo)
        git_ok("commit", "-qm", "init", cwd=self.repo)
        write_adapter(
            self.repo,
            """
verify:
  setup: python3 -c "open('setup-ran.txt', 'w').write('ok')"
  test_fast: python3 -c "open('baseline.txt', 'w').write('ok')"
worktree_dir: .worktrees
worktree_name_pattern: "{repo}-wt-{slug}"
branch_pattern: "{type}/{slug}"
""",
        )

    def create(self, *arguments):
        return run(WORKTREE, "--repo", self.repo, *arguments)

    def target(self, slug):
        return self.repo / ".worktrees" / ("%s-wt-%s" % (self.repo.name, slug))

    def test_dry_run_creates_nothing(self):
        result = self.create("--slug", "demo", "--dry-run", "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertFalse((self.repo / ".worktrees").exists())
        self.assertIn("git", result.stderr)  # printed plan, on stderr in --json mode

    def test_creates_worktree_branch_copy_setup_baseline(self):
        result = self.create(
            "--slug",
            "demo",
            "--type",
            "feature",
            "--copy",
            ".env.example",
            "--setup",
            "--baseline",
        )
        self.assert_rc(result, 0)
        worktree = self.target("demo")
        self.assertTrue((worktree / "README.md").is_file())
        self.assertEqual(
            git_ok("rev-parse", "--abbrev-ref", "HEAD", cwd=worktree), "feature/demo"
        )
        self.assertTrue((worktree / "setup-ran.txt").is_file())
        self.assertTrue((worktree / "baseline.txt").is_file())
        self.assertTrue((worktree / ".env.example").is_file())
        branches = git_ok("branch", "--list", "feature/demo", cwd=self.repo)
        self.assertIn("feature/demo", branches)
        worktrees = git_ok("worktree", "list", cwd=self.repo)
        self.assertIn(str(worktree), worktrees)

    def test_refuses_existing_path_and_never_deletes(self):
        self.assert_rc(self.create("--slug", "one"), 0)
        first = self.target("one")
        self.assert_rc(self.create("--slug", "one"), 1)
        self.assertTrue(first.exists())
        self.assert_rc(self.create("--slug", "two"), 0)
        self.assertTrue(first.exists())
        self.assertTrue(self.target("two").exists())
        listed = git_ok("worktree", "list", cwd=self.repo)
        self.assertIn(str(first), listed)
        self.assertIn(str(self.target("two")), listed)

    def test_refuses_existing_branch(self):
        git_ok("branch", "feature/taken", cwd=self.repo)
        result = self.create("--slug", "taken")
        self.assert_rc(result, 1)
        self.assertIn("already exists", result.stderr)
        self.assertFalse(self.target("taken").exists())

    def test_refuses_force_flag(self):
        result = self.create("--slug", "x", "--force")
        self.assert_rc(result, 2)
        self.assertIn("never", result.stderr)

    def test_refuses_outside_repo(self):
        outside = Path(self.temp.name) / "plain"
        outside.mkdir()
        result = run(WORKTREE, "--repo", outside, "--slug", "x")
        self.assert_rc(result, 1)
        self.assertIn("not a git repository", result.stderr)

    def test_missing_ticket_token_is_actionable(self):
        write_adapter(
            self.repo,
            """
worktree_dir: .worktrees
worktree_name_pattern: "{repo}-wt-{slug}"
branch_pattern: "{type}/{ticket}-{slug}"
""",
        )
        result = self.create("--slug", "x")
        self.assert_rc(result, 1)
        self.assertIn("--ticket", result.stderr)

    def test_unsupported_token_is_actionable(self):
        write_adapter(
            self.repo,
            """
worktree_dir: .worktrees
worktree_name_pattern: "{repo}-wt-{slug}"
branch_pattern: "{typo}/{slug}"
""",
        )
        result = self.create("--slug", "x")
        self.assert_rc(result, 1)
        self.assertIn("unsupported token", result.stderr)

    def test_setup_failure_leaves_worktree_for_inspection(self):
        write_adapter(
            self.repo,
            """
verify:
  setup: python3 -c "import sys; sys.exit(1)"
worktree_dir: .worktrees
worktree_name_pattern: "{repo}-wt-{slug}"
branch_pattern: "{type}/{slug}"
""",
        )
        result = self.create("--slug", "broken", "--setup")
        self.assert_rc(result, 1)
        self.assertTrue(self.target("broken").exists())


# --------------------------------------------------------------------------------------
# traceability.py
# --------------------------------------------------------------------------------------


class TraceabilityTests(ScriptTestCase):
    def write(self, text):
        path = self.root / "spec.md"
        path.write_text(text)
        return path

    GOOD = """# Feature

## Acceptance Criteria

- **AC-1**: User can log in.
- **AC-2**: Invalid password shows an error.

## Traceability

| AC | Task | Proof |
|---|---|---|
| AC-1 | T1 login endpoint | `python3 -m pytest tests/auth` |
| AC-2 | T2 error branch | `python3 -m pytest tests/errors` |

## Tasks

- [ ] T1 login endpoint (AC-1)
- [ ] T2 error branch (AC-2)
"""

    def test_valid_spec_passes_and_json_parses(self):
        path = self.write(self.GOOD)
        before = path.read_bytes()
        result = run(TRACEABILITY, "--file", path, "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["criteria"], 2)
        self.assertEqual(payload["summary"]["rows"], 2)
        self.assertEqual(path.read_bytes(), before)  # read-only
        human = run(TRACEABILITY, "--file", path)
        self.assert_rc(human, 0)
        self.assertIn("OK:", human.stdout)

    def test_missing_proof_fails(self):
        path = self.write(
            self.GOOD.replace("`python3 -m pytest tests/errors`", " ")
        )
        result = run(TRACEABILITY, "--file", path)
        self.assert_rc(result, 1)
        self.assertIn("missing proof for AC-2", result.stdout)

    def test_duplicate_criterion_and_row_fail(self):
        path = self.write(
            self.GOOD.replace(
                "- **AC-2**: Invalid password shows an error.",
                "- **AC-1**: duplicate.\n- **AC-3**: no row.",
            )
        )
        result = run(TRACEABILITY, "--file", path, "--json")
        self.assert_rc(result, 1)
        payload = json.loads(result.stdout)
        codes = {problem["code"] for problem in payload["problems"]}
        self.assertIn("duplicate_ac", codes)
        self.assertIn("missing_row", codes)

    def test_orphan_row_fails(self):
        path = self.write(
            self.GOOD.replace("| AC-2 | T2 error branch |", "| AC-9 | T2 error branch |")
        )
        result = run(TRACEABILITY, "--file", path)
        self.assert_rc(result, 1)
        self.assertIn("AC-9", result.stdout)
        self.assertIn("not defined", result.stdout)

    def test_unlabelled_criterion_is_actionable(self):
        path = self.write(
            self.GOOD.replace(
                "- **AC-2**: Invalid password shows an error.",
                "- Invalid password shows an error.",
            )
        )
        result = run(TRACEABILITY, "--file", path)
        self.assert_rc(result, 1)
        self.assertIn("no stable id", result.stdout)

    def test_no_criteria_fails(self):
        path = self.write("# Feature\n\nNothing here.\n")
        result = run(TRACEABILITY, "--file", path)
        self.assert_rc(result, 1)
        self.assertIn("no acceptance criteria", result.stdout)


    SPEC_KIT_SPEC = """# Feature Specification

## Success Criteria

- **SC-001**: Locate scope and decisions in one minute.
- **SC-002**: Local edits are reflected within two seconds.
- **SC-003**: Stale writes keep the observed external changes.

## Assumptions

One project per process.
"""

    @staticmethod
    def spec_kit_table(rows):
        return (
            "\n## Traceability\n\n"
            "| Criterion | Task | Proof |\n"
            "|---|---|---|\n" + rows
        )

    def test_spec_kit_success_criteria_without_rows_warns_but_passes(self):
        path = self.write(self.SPEC_KIT_SPEC)
        result = run(TRACEABILITY, "--file", path, "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(
            [item["id"] for item in payload["acceptance_criteria"]],
            ["SC-001", "SC-002", "SC-003"],
        )
        self.assertEqual(payload["summary"]["problems"], 0)
        self.assertGreaterEqual(payload["summary"]["warnings"], 1)
        human = run(TRACEABILITY, "--file", path)
        self.assert_rc(human, 0)
        self.assertIn("SC-001", human.stdout)

    def test_require_rows_flags_a_plain_spec(self):
        path = self.write(self.SPEC_KIT_SPEC)
        result = run(TRACEABILITY, "--file", path, "--require-rows")
        self.assert_rc(result, 1)
        self.assertIn("traceability", result.stdout)
        payload = run(TRACEABILITY, "--file", path, "--require-rows", "--json")
        body = json.loads(payload.stdout)
        self.assertTrue(body["require_rows"])
        self.assertFalse(body["ok"])

    def test_spec_kit_success_criteria_with_traceability_table_passes(self):
        rows = (
            "| SC-001 | T1 | `python3 -m pytest tests/scope` |\n"
            "| SC-002 | T2 | `python3 -m pytest tests/browser` |\n"
            "| SC-003 | T3 | `python3 -m pytest tests/stale` |\n"
        )
        path = self.write(self.SPEC_KIT_SPEC + self.spec_kit_table(rows))
        result = run(TRACEABILITY, "--file", path, "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["criteria"], 3)
        self.assertEqual(payload["summary"]["rows"], 3)
        self.assertEqual(
            [row["id"] for row in payload["rows"]], ["SC-001", "SC-002", "SC-003"]
        )
        self.assertEqual([row["proof"] for row in payload["rows"]],
                         ["`python3 -m pytest tests/scope`",
                          "`python3 -m pytest tests/browser`",
                          "`python3 -m pytest tests/stale`"])

    def test_spec_kit_missing_row_fails_actionably(self):
        rows = (
            "| SC-001 | T1 | `python3 -m pytest tests/scope` |\n"
            "| SC-002 | T2 | `python3 -m pytest tests/browser` |\n"
        )
        path = self.write(self.SPEC_KIT_SPEC + self.spec_kit_table(rows))
        result = run(TRACEABILITY, "--file", path)
        self.assert_rc(result, 1)
        self.assertIn("SC-003 has no traceability row", result.stdout)

    def test_spec_kit_missing_proof_fails_actionably(self):
        rows = (
            "| SC-001 | T1 | `python3 -m pytest tests/scope` |\n"
            "| SC-002 | T2 |  |\n"
            "| SC-003 | T3 | `python3 -m pytest tests/stale` |\n"
        )
        path = self.write(self.SPEC_KIT_SPEC + self.spec_kit_table(rows))
        result = run(TRACEABILITY, "--file", path)
        self.assert_rc(result, 1)
        self.assertIn("missing proof for SC-002", result.stdout)

    def test_intaking_ticket_table_convention_passes(self):
        path = self.write(
            """# Ticket

## Acceptance Criteria

- **AC-01**: Login succeeds with valid credentials.
- **AC-02**: The error copy is understandable to a person.

## Traceability

| Criterion | Rule(s) it enforces | Bucket | Proven by | Acceptance case |
|---|---|---|---|---|
| AC-01 | BR-01 | machine | `python3 -m pytest tests/auth` | — |
| AC-02 | BR-02 | person | — | UAT-01 |
"""
        )
        result = run(TRACEABILITY, "--file", path, "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["rows"], 2)
        # A person-checked row may be proven by its acceptance case instead of a command.
        self.assertEqual(payload["rows"][1]["proof"], "UAT-01")
        self.assertEqual(payload["rows"][1].get("proof_source"), "acceptance_case")

    def test_errors(self):
        result = run(TRACEABILITY, "--file", self.root / "missing.md")
        self.assert_rc(result, 1)
        self.assertIn("not found", result.stderr)
        result = run(TRACEABILITY)
        self.assert_rc(result, 2)
        result = run(TRACEABILITY, "--help")
        self.assert_rc(result, 0)
        self.assertIn("--file", result.stdout)


# --------------------------------------------------------------------------------------
# check_skills.py (Lead-owned, tested here for P1.0 T01 acceptance)
# --------------------------------------------------------------------------------------


class CheckSkillsTests(ScriptTestCase):
    @classmethod
    def setUpClass(cls):
        if not CHECK_SKILLS.is_file():
            raise unittest.SkipTest("scripts/check_skills.py not present")

    def make_kit(self, root, name="valid-skill", description=None):
        root = Path(root)
        skill = root / "skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True)
        description = description or "Use when checking fixtures. Not for production."
        skill.write_text(
            "---\nname: %s\ndescription: %s\n---\n\n# %s\n\nBody.\n"
            % (name, description, name)
        )
        return skill

    def check(self, *arguments):
        return run(CHECK_SKILLS, *arguments)

    def test_valid_single_root_kit_passes(self):
        kit = self.root / "kit"
        self.make_kit(kit)
        result = self.check(kit, "--kit", kit)
        self.assert_rc(result, 0)
        self.assertIn("OK:", result.stdout)

    def test_name_mismatch_fails(self):
        kit = self.root / "kit"
        skill = self.make_kit(kit)
        skill.write_text(skill.read_text().replace("name: valid-skill", "name: other"))
        result = self.check(kit)
        self.assert_rc(result, 1)
        self.assertIn("must equal the directory name", result.stdout)

    def test_parity_drift_fails(self):
        project = self.root / "project"
        canonical = project / ".agents" / "skills" / "foo" / "SKILL.md"
        mirror = project / ".claude" / "skills" / "foo" / "SKILL.md"
        canonical.parent.mkdir(parents=True)
        mirror.parent.mkdir(parents=True)
        canonical.write_text(
            "---\nname: foo\ndescription: Use when canonical. Not for mirrors.\n---\nBody.\n"
        )
        mirror.write_text(
            "---\nname: foo\ndescription: Use when drifted. Not for mirrors.\n---\nBody.\n"
        )
        result = self.check(project)
        self.assert_rc(result, 1)
        self.assertIn("differs from canonical", result.stdout)

    def test_require_trigger_flags_missing_phrases(self):
        kit = self.root / "kit"
        self.make_kit(kit, description="Checks fixtures.")
        ok = self.check(kit)
        self.assert_rc(ok, 0)
        result = self.check(kit, "--require-trigger")
        self.assert_rc(result, 1)
        self.assertIn("Use when", result.stdout)
        self.assertIn("Not for", result.stdout)

    def test_json_payload_parses(self):
        kit = self.root / "kit"
        self.make_kit(kit)
        result = self.check(kit, "--json")
        self.assert_rc(result, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["skills"], 1)
        self.assertIn("details", payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
