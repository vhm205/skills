#!/usr/bin/env python3
"""Offline contracts and adversarial checks for eval v2. No model calls."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from _eval.contracts import ContractError, validate, validate_suite
from _eval.reporting import aggregate, grade_dimensions, markdown_report

KIT = Path(__file__).resolve().parent.parent


def assertion(dimension, passed, **extra):
    return {"id": dimension, "dimension": dimension, "required": True,
            "critical": False, "status": "pass" if passed else "fail",
            "evidence": "observed", **extra}


def trial(name="t1", variant="full-kit", **extra):
    return {"schema": "aiek-eval-trial/2", "id": name, "scenario": "bug",
            "variant": variant, "repeat": 0, "status": "completed", "synthetic": False,
            "duration_s": 2.0, "usage": {"total_tokens": 10},
            "assertions": [assertion("outcome", True)], "error": None, **extra}


class ContractTests(unittest.TestCase):
    def test_suite_requires_model_for_real_execution_but_not_planning(self):
        suite = {"schema": "aiek-eval-suite/2", "id": "pilot", "harness": "dsh",
                 "model": None, "scenarios": ["bug"], "variants": ["no-kit", "full-kit"],
                 "repeats": 3, "max_trials": 6, "timeout_s": 10, "seed": 42}
        validate_suite(suite, planning=True)
        with self.assertRaises(ContractError):
            validate_suite(suite)
        suite["model"] = "pinned-model"
        validate_suite(suite)

    def test_invalid_or_over_budget_suite_fails_before_execution(self):
        suite = {"schema": "aiek-eval-suite/2", "id": "pilot", "harness": "mock",
                 "model": None, "scenarios": ["bug"], "variants": ["no-kit", "full-kit"],
                 "repeats": 3, "max_trials": 5, "timeout_s": 10, "seed": 42}
        with self.assertRaises(ContractError):
            validate_suite(suite)
        suite["max_trials"] = 6
        suite["repeats"] = True
        with self.assertRaises(ContractError):
            validate_suite(suite)

    def test_schema_rejects_malformed_trial(self):
        validate("trial", trial())
        bad = trial(duration_s=-1)
        with self.assertRaises(ContractError):
            validate("trial", bad)


class ScoringTests(unittest.TestCase):
    def test_golden_accounting_with_pending_error_and_critical_trial(self):
        data = json.loads((KIT / "evals/tests/accounting.json").read_text())
        actual = aggregate(data["trials"])["variants"]["full-kit"]
        self.assertEqual({k:actual[k] for k in data["expected"]},data["expected"])
    def test_correct_code_missing_lane_passes_outcome(self):
        grades = grade_dimensions([assertion("outcome", True), assertion("compliance", False)])
        self.assertEqual(grades["outcome"], "pass")
        self.assertEqual(grades["compliance"], "fail")

    def test_pretty_report_does_not_override_failed_code(self):
        grades = grade_dimensions([assertion("outcome", False), assertion("compliance", True)])
        self.assertEqual(grades["outcome"], "fail")

    def test_optional_failure_does_not_fail_required_outcome(self):
        grades = grade_dimensions([assertion("outcome", True),
                                   assertion("outcome", False, required=False)])
        self.assertEqual(grades["outcome"], "pass")

    def test_missing_or_pending_grader_cannot_pass(self):
        self.assertEqual(grade_dimensions([])["outcome"], "unavailable")
        self.assertEqual(grade_dimensions([assertion("outcome", True),
                         assertion("outcome", True, status="pending-review")])["outcome"],
                         "pending-review")

    def test_critical_action_failure_overrides_success(self):
        grades = grade_dimensions([assertion("outcome", True),
                                   assertion("safety", False, critical=True)])
        self.assertEqual(grades["outcome"], "fail")
        self.assertEqual(grades["critical_violations"], 1)

    def test_all_trials_count_and_one_critical_is_not_hidden_by_majority(self):
        rows = [trial("a"), trial("b", usage={"total_tokens": 20}),
                trial("c", assertions=[assertion("outcome", False, critical=True)],
                      usage={"total_tokens": 30})]
        summary = aggregate(rows)["variants"]["full-kit"]
        self.assertEqual(summary["successes"], 2)
        self.assertEqual(summary["graded"], 3)
        self.assertAlmostEqual(summary["quality_rate"], 2 / 3)
        self.assertEqual(summary["total_tokens"], 60)
        self.assertEqual(summary["duration_s"], 6)
        self.assertEqual(summary["critical_violations"], 1)
        self.assertFalse(summary["all_trials_success"])

    def test_errors_remain_in_end_to_end_denominator(self):
        rows = [trial(), trial("b", status="timeout", assertions=[], usage={})]
        summary = aggregate(rows)["variants"]["full-kit"]
        self.assertEqual(summary["quality_rate"], 1)
        self.assertEqual(summary["end_to_end_rate"], .5)
        self.assertEqual(summary["coverage"], .5)
        self.assertIsNone(summary["total_tokens"])
        self.assertEqual(summary["known_tokens"], 10)
        self.assertEqual(summary["errors"], 1)

    def test_planned_is_not_success_or_started(self):
        summary = aggregate([trial(status="planned", assertions=[], usage={})])["variants"]["full-kit"]
        self.assertEqual(summary["started"], 0)
        self.assertEqual(summary["successes"], 0)
        self.assertIsNone(summary["quality_rate"])

    def test_synthetic_and_real_cannot_be_mixed(self):
        with self.assertRaises(ContractError):
            aggregate([trial(), trial("b", synthetic=True)])

    def test_paired_task_delta_and_markdown_explain_denominators(self):
        report = aggregate([trial("a", "no-kit", assertions=[assertion("outcome", False)]), trial("b")])
        self.assertEqual(report["per_scenario"][0]["delta"], 1)
        self.assertIn("coverage", markdown_report(report).lower())


class ProcessTests(unittest.TestCase):
    def test_timeout_kills_child_process_not_only_parent(self):
        from _eval.process import run_process
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "escaped"
            child = f"import time;from pathlib import Path;time.sleep(.7);Path({str(marker)!r}).write_text('escaped')"
            parent = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}]);time.sleep(10)"
            rc, _, err, _, _ = run_process([sys.executable, "-c", parent], cwd=Path(tmp), timeout=.15)
            self.assertIsNone(rc)
            self.assertIn("timeout", err)
            time.sleep(.8)
            self.assertFalse(marker.exists())

    def test_output_is_bounded_and_overflow_is_an_error(self):
        from _eval.process import run_process
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, err, _, _ = run_process([sys.executable, "-c", "print('x'*100000)"],
                                           cwd=Path(tmp), timeout=2, max_output_bytes=2048)
            self.assertIsNone(rc)
            self.assertLessEqual(len(out), 2048)
            self.assertIn("output limit", err)


class HarnessTests(unittest.TestCase):
    @unittest.skipUnless(__import__('shutil').which('node'), 'Node needed for trusted DSH bootstrap test')
    def test_dsh_bootstrap_redacts_file_loaded_credential_before_capture(self):
        from unittest.mock import patch
        from _eval.dsh import run_isolated, boot_module
        import shutil
        original_which = shutil.which
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            work.mkdir()
            binary = root / "package/lib/dsh"
            binary.parent.mkdir(parents=True)
            binary.write_text(f"#!{sys.executable}\nimport os,json,tempfile\nprint(json.dumps({{'type':'text','text':os.environ['DEEPSEEK_API_KEY']+' TEMP='+str(tempfile.mkdtemp(prefix='dsh-subprocess-'))}}))\n")
            binary.chmod(0o755)
            boot = boot_module(str(binary))
            boot.parent.mkdir(parents=True)
            (boot.parent / "package.json").write_text('{"type":"module"}')
            boot.write_text("export function loadLayeredEnv(){process.env.DEEPSEEK_API_KEY='opaque-test-credential-123';}")
            paths = boot.parent.parent.parent / "dsh-home-paths/lib"
            paths.mkdir(parents=True)
            (paths / "package.json").write_text('{"type":"module"}')
            (paths / "index.js").write_text("export function resolveDshHome(){return " + json.dumps(str(root / 'no-home')) + ";}")
            fake_sandbox = root / "fake-sandbox"
            fake_sandbox.write_text('#!/bin/sh\nshift 2\nexec "$@"\n')
            fake_sandbox.chmod(0o755)
            with patch("_eval.dsh.shutil.which", side_effect=lambda n: str(fake_sandbox) if n == "sandbox-exec" else original_which(n)):
                response = run_isolated(str(binary),"prompt",work,root,KIT,"model-a",dict(os.environ),5)
            self.assertIsNone(response.error)
            self.assertNotIn('opaque-test-credential-123',response.raw_stdout)
            self.assertIn('[REDACTED]',response.text)
            created = Path(response.text.split(' TEMP=',1)[1].strip()).resolve()
            created.rmdir()
            self.assertTrue(created.is_relative_to(root.resolve()), 'DSH subprocess temp must stay within sandbox writable root')

    @unittest.skipUnless(__import__('shutil').which('node'), 'Node needed for credential boundary test')
    def test_dsh_stored_credential_precedence_permissions_and_redaction(self):
        from unittest.mock import patch
        from _eval.dsh import authentication_available, run_isolated, boot_module
        import shutil
        original_which = shutil.which
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            work.mkdir()
            home = root / "user-home"
            home.mkdir()
            binary = root / "package/lib/dsh"
            binary.parent.mkdir(parents=True)
            binary.write_text(f"#!{sys.executable}\nimport os,json\nprint(json.dumps({{'type':'text','text':('STORED:' if os.environ['DEEPSEEK_API_KEY']=='stored-opaque-secret' else 'FALLBACK:')+os.environ['DEEPSEEK_API_KEY']}}))\n")
            binary.chmod(0o755)
            boot = boot_module(str(binary))
            boot.parent.mkdir(parents=True)
            (boot.parent / "package.json").write_text('{"type":"module"}')
            boot.write_text("export function loadLayeredEnv(){delete process.env.DEEPSEEK_API_KEY;}")
            packages = boot.parent.parent.parent
            for name, source in {
                "dsh-home-paths": "export function resolveDshHome(){return process.env.DSH_HOME;}",
                "dsh-credentials-local": "export function parseCredentialsDocument(s){const d=JSON.parse(s);return {refs:new Map(Object.entries(d.refs))};}",
            }.items():
                module = packages / name / "lib"
                module.mkdir(parents=True)
                (module / "package.json").write_text('{"type":"module"}')
                (module / "index.js").write_text(source)
            credentials = home / ".credentials.yaml"
            credentials.write_text(json.dumps({"refs":{"DEEPSEEK_API_KEY":"stored-opaque-secret"}}))
            credentials.chmod(0o600)
            fake_sandbox = root / "fake-sandbox"
            fake_sandbox.write_text('#!/bin/sh\nshift 2\nexec "$@"\n')
            fake_sandbox.chmod(0o755)
            environment = {**os.environ, "DSH_HOME": str(home)}
            with patch.dict(os.environ, environment, clear=True):
                self.assertTrue(authentication_available(str(binary)), "stored official key must count")
            boot.write_text("export function loadLayeredEnv(){process.env.DEEPSEEK_API_KEY='env-fallback-secret';}")
            with patch("_eval.dsh.shutil.which", side_effect=lambda n: str(fake_sandbox) if n == "sandbox-exec" else original_which(n)):
                response = run_isolated(str(binary),"prompt",work,root,KIT,"model-a",environment,5)
            self.assertIsNone(response.error)
            self.assertIn('STORED:[REDACTED]',response.text)
            self.assertNotIn('stored-opaque-secret',response.raw_stdout + response.raw_stderr)
            self.assertNotIn('env-fallback-secret',response.raw_stdout + response.raw_stderr)
            self.assertEqual(credentials.read_text(),json.dumps({"refs":{"DEEPSEEK_API_KEY":"stored-opaque-secret"}}))
            credentials.chmod(0o644)
            with patch.dict(os.environ, environment, clear=True):
                self.assertFalse(authentication_available(str(binary)), "unsafe store must fail closed, not use env fallback")
            credentials.chmod(0o600)
            credentials.write_text('invalid credential document stored-opaque-secret')
            with patch.dict(os.environ, environment, clear=True):
                self.assertFalse(authentication_available(str(binary)), "invalid store must fail closed")

    def test_codex_failed_turn_does_not_pass_with_partial_answer(self):
        from unittest.mock import patch
        from _eval.harnesses import CodexHarness
        h = object.__new__(CodexHarness)
        h.binary = "codex"
        stream = '\n'.join(json.dumps(e) for e in [
            {"type":"item.completed","item":{"type":"agent_message","text":"Working"}},
            {"type":"turn.failed","error":{"message":"provider failed"}}])
        with patch("_eval.harnesses.run_process", return_value=(0,stream,"",1,[])):
            r = h.run("prompt", Path.cwd(), None, 10)
        self.assertIsNotNone(r.error)
        self.assertEqual(len(r.events), 2)

    def test_claude_usage_and_skill_events_have_provenance(self):
        from unittest.mock import patch
        from _eval.harnesses import ClaudeHarness
        h = object.__new__(ClaudeHarness)
        h.binary = "claude"
        raw = {"result":"Done", "usage":{"input_tokens":7,"output_tokens":3},
               "messages":[{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"aiek-executing-task"}}]}]}
        with patch("_eval.harnesses.run_process", return_value=(0,json.dumps(raw),"",1,[])):
            r = h.run("prompt",Path.cwd(),None,10)
        self.assertEqual(r.source,"tool_call")
        self.assertEqual(r.skills_used,["executing-task"])
        self.assertEqual(r.usage["totalTokens"],10)

    def test_dsh_errors_are_not_hidden_by_earlier_text(self):
        from _eval.harnesses import DshHarness
        h = object.__new__(DshHarness)
        r = h.parse('{"type":"text","text":"Done"}\n{"type":"error","message":"failed"}', "", 1, 2)
        self.assertIsNotNone(r.error)

    def test_dsh_invalid_stream_is_error(self):
        from _eval.harnesses import DshHarness
        r = object.__new__(DshHarness).parse("not-json", "", 1, 2)
        self.assertIsNotNone(r.error)

    def test_usage_is_unknown_when_one_completed_step_has_no_sample(self):
        from _eval.harnesses import DshHarness
        stream = '\n'.join(json.dumps(e) for e in [
            {"type":"text", "text":"Done"},
            {"type":"status", "phase":"step_end", "usage":{"totalTokens":30}},
            {"type":"status", "phase":"step_end"}])
        r = object.__new__(DshHarness).parse(stream, "", 1, 2)
        self.assertEqual(r.usage, {})

    def test_usage_missing_is_unknown(self):
        from _eval.harnesses import normalized_usage
        self.assertEqual(normalized_usage({}), {})
        self.assertEqual(normalized_usage({"outputTokens": 3}), {"output_tokens": 3})
        self.assertEqual(normalized_usage({"totalTokens": 30}), {"total_tokens": 30})


class WorkspaceTests(unittest.TestCase):
    def test_setup_rejects_traversal_and_snapshot_rejects_symlinks(self):
        from _eval.workspace import write_setup, snapshot
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "work"
            root.mkdir()
            with self.assertRaises(ContractError):
                write_setup(root, [("../escape", "x")])
            (root / "link").symlink_to(Path(tmp))
            with self.assertRaises(ContractError):
                snapshot(root)

    def test_redaction_happens_before_writing_and_records_are_immutable(self):
        from _eval.runner import EvidenceStore
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp), {"id": "exp"}, secrets=["private-value-123"])
            store.write_once("trial.json", {"text": "Bearer private-value-123", "key": "sk-proj-abcdef1234567890"})
            content = (Path(tmp) / "trial.json").read_text()
            self.assertNotIn("private-value-123", content)
            self.assertNotIn("sk-proj-abcdef1234567890", content)
            with self.assertRaises(ContractError):
                store.write_once("trial.json", {})
            with self.assertRaises(ContractError):
                EvidenceStore(Path(tmp), {"id": "other"})


class GraderTests(unittest.TestCase):
    def test_small_copy_grader_rejects_correct_words_with_changed_behavior(self):
        import eval_tasks
        from _eval.graders import grade_copy
        from _eval.workspace import write_setup
        fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/01-small-fix.md")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_setup(root, fixture["setup"])
            self.assertEqual(grade_copy(fixture, root)[0]["status"], "fail")
            write_setup(root, fixture["mock_changes"])
            self.assertEqual(grade_copy(fixture, root)[0]["status"], "pass")
            target = root / "src/emails/signup.ts"
            target.write_text(target.read_text().replace("Thanks for signing up.", "Send your password."))
            self.assertEqual(grade_copy(fixture, root)[0]["status"], "fail")


    def setUp(self):
        import eval_tasks
        self.fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/03-bug.md")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        from _eval.workspace import write_setup
        write_setup(self.root, self.fixture["setup"])

    def test_plus_email_oracle_rejects_noop_and_accepts_general_fix(self):
        from _eval.graders import grade_bug
        self.assertEqual(grade_dimensions(grade_bug(self.fixture, self.root))["outcome"], "fail")
        source = self.root / "app/auth.py"
        source.write_text(source.read_text().replace('local.split("+")[1]', 'local.split("+")[0]'))
        self.assertEqual(grade_dimensions(grade_bug(self.fixture, self.root))["outcome"], "pass")

    def test_hardcode_and_deleted_code_do_not_pass(self):
        from _eval.graders import grade_bug
        source = self.root / "app/auth.py"
        source.write_text('def normalize_email(email): return "alice@example.com"\n'
                          'def find_user(email): return {"id": 1}\n')
        self.assertEqual(grade_dimensions(grade_bug(self.fixture, self.root))["outcome"], "fail")
        source.unlink()
        self.assertEqual(grade_dimensions(grade_bug(self.fixture, self.root))["outcome"], "fail")

    def test_test_tampering_and_configuration_change_cannot_game_oracle(self):
        from _eval.graders import grade_bug
        source = self.root / "app/auth.py"
        source.write_text(source.read_text().replace('local.split("+")[1]', 'local.split("+")[0]'))
        (self.root / "tests/test_auth.py").write_text("# disable tests\n")
        self.assertEqual(grade_dimensions(grade_bug(self.fixture, self.root))["outcome"], "fail")

    def test_semantic_outcome_requires_label_even_when_keywords_present(self):
        from _eval.graders import human_outcome
        grade = human_outcome("review-diff", "CRITICAL tenant IDOR restore", "t1", "hash")
        self.assertEqual(grade["status"], "pending-review")
        label = {"trial_id": "t1", "artifact_hash": "hash", "rubric_version": "review-diff/1",
                 "passed": False, "evidence": "Keywords without a supported finding", "reviewer": "human"}
        grade = human_outcome("review-diff", "CRITICAL tenant IDOR restore", "t1", "hash", label)
        self.assertEqual(grade["status"], "fail")
        label["artifact_hash"] = "stale"
        with self.assertRaises(ContractError):
            human_outcome("review-diff", "text", "t1", "hash", label)


class ExperimentTests(unittest.TestCase):
    def test_candidate_config_tampering_is_detected_even_with_correct_code(self):
        import eval_tasks
        from _eval.runner import EvidenceStore, execute, make_manifest
        fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/03-bug.md")
        fixture["mock_changes"].append(("setup.cfg", "[tool]\ndisable_tests=true"))
        suite = {"schema": "aiek-eval-suite/2", "id": "config-tamper", "harness": "mock", "model": None,
                 "scenarios": ["bug"], "variants": ["full-kit"],
                 "repeats": 1, "max_trials": 1, "timeout_s": 10, "seed": 0}
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp), make_manifest(suite, [fixture], KIT, {"name":"mock"}))
            report = execute(suite, [fixture], KIT, store)
            self.assertEqual(report["variants"]["full-kit"]["successes"],0)
            self.assertEqual(report["variants"]["full-kit"]["critical_violations"],1)

    def test_lite_variant_installs_only_lite_profile_and_keeps_outcome_grading(self):
        import eval_tasks
        from _eval.runner import EvidenceStore, execute, make_manifest
        fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/03-bug.md")
        suite = {"schema": "aiek-eval-suite/2", "id": "lite", "harness": "mock", "model": None,
                 "scenarios": ["bug"], "variants": ["lite-kit"],
                 "repeats": 1, "max_trials": 1, "timeout_s": 10, "seed": 0}
        validate_suite(suite)
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp), make_manifest(suite, [fixture], KIT, {"name": "mock"}))
            report = execute(suite, [fixture], KIT, store)
            row = report["trials"][0]
            self.assertEqual(row["install"]["profile"], "lite")
            expected = json.loads((KIT / "manifest.json").read_text())["profiles"]["lite"]
            self.assertEqual(row["install"]["skills"], sorted("aiek-" + s for s in expected))
            self.assertEqual(report["variants"]["lite-kit"]["successes"], 1)
            self.assertTrue(row["synthetic"])

    def test_install_failure_stops_before_agent_and_keeps_error_record(self):
        import eval_tasks
        from unittest.mock import patch
        from _eval.runner import EvidenceStore, execute, make_manifest
        fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/03-bug.md")
        suite = {"schema": "aiek-eval-suite/2", "id": "install-fail", "harness": "mock", "model": None,
                 "scenarios": ["bug"], "variants": ["full-kit"],
                 "repeats": 1, "max_trials": 1, "timeout_s": 10, "seed": 0}
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp), make_manifest(suite, [fixture], KIT, {"name":"mock"}))
            with patch("_eval.runner.install", side_effect=ContractError("install-error: failed")):
                report = execute(suite, [fixture], KIT, store)
            self.assertEqual(report["trials"][0]["status"], "install-error")
            self.assertFalse((Path(tmp)/"artifacts").exists())
            self.assertEqual(report["variants"]["full-kit"]["errors"], 1)

    def test_interrupted_slot_is_not_automatically_retried(self):
        import eval_tasks
        from _eval.runner import EvidenceStore, execute, make_manifest
        fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/03-bug.md")
        suite = {"schema": "aiek-eval-suite/2", "id": "interrupted", "harness": "mock", "model": None,
                 "scenarios": ["bug"], "variants": ["no-kit"],
                 "repeats": 1, "max_trials": 1, "timeout_s": 10, "seed": 0}
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp), make_manifest(suite, [fixture], KIT, {"name":"mock"}))
            store.write_once("trials/trial-0000.started.json", {"status":"started"})
            report = execute(suite, [fixture], KIT, store, resume=True)
            self.assertEqual(report["trials"][0]["status"], "interrupted")
            self.assertFalse((Path(tmp)/"artifacts").exists())

    def test_fixture_rejects_unknown_outcome_grader(self):
        import eval_tasks
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "bad.md"
            original = (KIT / "evals/tasks/03-bug.md").read_text()
            fixture.write_text(original.replace('"kind": "plus-email"', '"kind": "always-pass"'))
            with self.assertRaises((ContractError, eval_tasks.FixtureError)):
                eval_tasks.parse_fixture(fixture)

    def test_dry_run_and_resume_preserve_trials_and_manifest(self):
        import eval_tasks
        from _eval.runner import EvidenceStore, execute, make_manifest, schedule
        fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/03-bug.md")
        suite = {"schema": "aiek-eval-suite/2", "id": "tiny", "harness": "mock", "model": None,
                 "scenarios": ["bug"], "variants": ["no-kit", "full-kit"],
                 "repeats": 2, "max_trials": 4, "timeout_s": 10, "seed": 12}
        self.assertEqual(schedule(suite), schedule(suite))
        with tempfile.TemporaryDirectory() as tmp:
            manifest = make_manifest(suite, [fixture], KIT, {"name": "mock"})
            self.assertIn("scripts/verify.py",manifest["source_hashes"])
            store = EvidenceStore(Path(tmp), manifest)
            planned = execute(suite, [fixture], KIT, store, dry_run=True)
            self.assertEqual(len(planned["trials"]), 4)
            self.assertFalse(list((Path(tmp) / "trials").glob("*")))
            report = execute(suite, [fixture], KIT, store)
            self.assertTrue(report["synthetic"])
            self.assertEqual(report["variants"]["full-kit"]["successes"], 2)
            self.assertRegex(report["trials"][0]["baseline_commit"], r"^[0-9a-f]{40}$")
            persisted = {p.name: p.read_bytes() for p in (Path(tmp)/"trials").glob("*")}
            again = execute(suite, [fixture], KIT, store, resume=True)
            self.assertEqual(report, again)
            self.assertEqual(persisted, {p.name: p.read_bytes() for p in (Path(tmp)/"trials").glob("*")})

    def test_human_labels_regrade_without_changing_original_trial(self):
        import eval_tasks
        from _eval.runner import EvidenceStore, execute, make_manifest, regrade, blind_review
        fixture = eval_tasks.parse_fixture(KIT / "evals/tasks/05-review-diff.md")
        suite = {"schema": "aiek-eval-suite/2", "id": "human", "harness": "mock", "model": None,
                 "scenarios": ["review-diff"], "variants": ["full-kit"],
                 "repeats": 1, "max_trials": 1, "timeout_s": 10, "seed": 0}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = EvidenceStore(root, make_manifest(suite, [fixture], KIT, {"name":"mock"}))
            report = execute(suite, [fixture], KIT, store)
            self.assertEqual(report["variants"]["full-kit"]["pending_review"], 1)
            labels = blind_review(root, report)
            self.assertNotIn("variant", labels[0])
            self.assertIsNone(labels[0]["passed"])
            original = (root / "trials/trial-0000.json").read_bytes()
            labels[0].update(passed=False, reviewer="human-test-fixture", evidence="Known false finding in synthetic answer")
            graded = regrade(root, labels)
            self.assertEqual(graded["variants"]["full-kit"]["successes"], 0)
            self.assertEqual(original, (root / "trials/trial-0000.json").read_bytes())

    def test_default_cli_is_v2_and_explicit_v1_remains_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            command = [sys.executable, str(KIT / "scripts/eval_tasks.py"), "--mock",
                       "--scenario", "small-fix", "--out", str(path)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(path.read_text())["schema"], "aiek-eval-report/2")
            run = subprocess.run(command + ["--report-version", "1"], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            legacy = json.loads(path.read_text())
            self.assertEqual(legacy["schema"], "aiek-behavior-eval/1")
            self.assertTrue(legacy["legacy"])

    def test_real_preflight_is_read_only_and_reports_unsupported_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            command = [sys.executable, str(KIT/"scripts/eval_tasks.py"), "--harness", "dsh",
                       "--scenario", "bug", "--preflight", "--out", str(output)]
            p = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            report = json.loads(output.read_text())
            self.assertEqual(report["agent_calls"], 0)
            self.assertIn("model_selection", report["missing_capabilities"])

    def test_dsh_model_patch_is_verified_without_agent_call(self):
        from _eval.dsh import model_patch, pinned_model
        self.assertEqual(model_patch("model-a")[0]["config"]["model"], "model-a")
        dump = "- id: agent-default-model\n  name: package\n  config:\n    provider: deepseek-official\n    model: model-a\n- id: other\n"
        self.assertEqual(pinned_model(dump), "model-a")
        with self.assertRaises(ContractError):
            model_patch("bad model\nsecret")


if __name__ == "__main__":
    unittest.main()
