"""Experiment scheduling, immutable evidence, offline replay and trial execution."""
from __future__ import annotations

from contextlib import contextmanager
import difflib
import json
import os
from pathlib import Path
import random
import re
import tempfile
import time

from .contracts import ContractError, digest, validate, validate_suite
from .graders import grade_copy, grade_bug, human_outcome, result
from .harnesses import DshHarness, ClaudeHarness, CodexHarness, describe, normalized_usage
from .reporting import aggregate, markdown_report
from .workspace import changed, commit_baseline, install, prepare_env, snapshot, write_setup


class EvidenceStore:
    def __init__(self, root: Path, manifest: dict, *, secrets: list[str] | None = None):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.secrets = [s for s in (secrets or []) if len(s) >= 8]
        self.manifest = manifest
        existing = self.root / "manifest.json"
        if existing.exists():
            saved = json.loads(existing.read_text())
            if saved.get("hash") != digest(manifest):
                raise ContractError("experiment manifest mismatch; use a new experiment directory")
        else:
            self.write_once("manifest.json", {"schema": "aiek-eval-manifest/2", "hash": digest(manifest),
                                               "inputs": manifest})

    def redact(self, value):
        if isinstance(value, dict):
            return {self.redact(k): self.redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if not isinstance(value, str):
            return value
        for secret in sorted(self.secrets, key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
        value = re.sub(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{12,}", "[REDACTED]", value)
        value = re.sub(r"(?im)((?:api[_-]?key|password|access[_-]?token|secret)\s*[:=]\s*)[^\s,;]+",
                       r"\1[REDACTED]", value)
        return value

    def _path(self, relative: str) -> Path:
        path = self.root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ContractError("evidence path escapes experiment")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_once(self, relative: str, value) -> None:
        path = self._path(relative)
        content = json.dumps(self.redact(value), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        fd, temporary = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)  # Atomic create; never overwrite previous evidence.
            except FileExistsError as exc:
                raise ContractError(f"immutable evidence already exists: {relative}") from exc
        finally:
            os.unlink(temporary)

    @contextmanager
    def lock(self):
        import fcntl
        with self._path(".lock").open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ContractError("experiment is already running") from exc
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def schedule(suite: dict) -> list[dict]:
    """Keep paired variants adjacent; randomize order with a recorded seed."""
    rng = random.Random(suite["seed"])
    pairs = [(scenario, repeat) for scenario in suite["scenarios"] for repeat in range(suite["repeats"])]
    rng.shuffle(pairs)
    rows = []
    for scenario, repeat in pairs:
        variants = list(suite["variants"])
        rng.shuffle(variants)
        for variant in variants:
            rows.append({"id": f"trial-{len(rows):04d}", "scenario": scenario,
                         "variant": variant, "repeat": repeat})
    return rows


def make_manifest(suite: dict, fixtures: list[dict], kit: Path, harness_info: dict) -> dict:
    sources = {}
    for folder in ("core", "skills", "adapters/default", "scripts/_eval"):
        for path in sorted((kit / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                sources[str(path.relative_to(kit))] = digest(path.read_bytes().hex())
    for name in ("scripts/install.sh", "scripts/eval_tasks.py", "scripts/eval_trigger.py",
                 "scripts/resolve_adapter.py", "scripts/verify.py", "scripts/worktree.py",
                 "scripts/traceability.py", "scripts/_adapter_yaml.py", "manifest.json", "package.json",
                 "evals/oracles/plus_email.py", "evals/labels/README.md"):
        sources[name] = digest((kit / name).read_bytes().hex())
    manifest = {"schema": "aiek-eval-experiment/2", "suite": suite, "harness": harness_info,
            "kit_content_hash": digest(sources), "source_hashes": sources,
            "fixtures": {f["id"]: digest(f) for f in fixtures}, "schedule": schedule(suite),
            "limits": {"max_primary_trials": suite["max_trials"], "automatic_retries": 0,
                       "max_output_bytes": 4 * 1024 * 1024},
            "model": {"requested": suite.get("model"), "observed": None},
            "network_policy": "inherited; no deployment fixture tools enabled",
            "release_proof": False}
    validate("experiment", manifest)
    return manifest


def _record(entry: dict, synthetic: bool) -> dict:
    return {"schema": "aiek-eval-trial/2", **entry, "synthetic": synthetic,
            "status": "planned", "duration_s": 0.0, "usage": {}, "assertions": [], "error": None}


def _compliance(fixture: dict, text: str, root: Path, before: dict, after: dict, variant: str) -> list[dict]:
    import eval_tasks  # Legacy parser/assertion implementation; not a second harness.
    created = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    modified = sorted(p for p in before.keys() & after.keys() if before[p] != after[p])
    rows = []
    for spec in fixture["assertions"]:
        if variant == "no-kit":
            grade = result(spec["id"], None, "Kit-only compliance does not apply to baseline", dimension="compliance")
            grade["status"] = "not-applicable"
        else:
            observed = eval_tasks.evaluate_assertion(spec, text, root, created, modified, removed)
            grade = result(spec["id"], observed["passed"], observed["detail"], dimension="compliance",
                           required=spec.get("required", True), critical=spec.get("critical", False))
            grade["observation"] = "declared" if spec["kind"].startswith("output_") or spec["kind"] == "min_questions" else "filesystem"
        rows.append(grade)
    return rows


def _trial(entry: dict, fixture: dict, suite: dict, kit: Path, store: EvidenceStore, *, harness=None) -> dict:
    row = _record(entry, suite["harness"] == "mock")
    row["status"] = "started"
    started = time.monotonic()
    store.write_once(f"trials/{row['id']}.started.json", row)
    try:
        with tempfile.TemporaryDirectory(prefix="aiek-trial-") as tmp:
            base = Path(tmp)
            work = base / "work"
            work.mkdir()
            write_setup(work, fixture["setup"])
            from .process import run_process
            rc, _, err, _, _ = run_process(["git", "init", "-q"], cwd=work, timeout=15,
                                          env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
            if rc != 0:
                raise ContractError("harness-error: git init failed: " + err[-200:])
            row["install"] = install(kit, work, suite["harness"], profile="lite" if entry["variant"] == "lite-kit" else "full") if entry["variant"] != "no-kit" else None
            row["baseline_commit"] = commit_baseline(work)
            before = snapshot(work)
            env = prepare_env(base / "config", suite["harness"])
            if suite["harness"] == "mock":
                if entry["variant"] != "no-kit":
                    write_setup(work, fixture["mock_changes"])
                text = fixture["mock_response"] if entry["variant"] != "no-kit" else fixture["mock_response_without_kit"]
                raw = {"text": text, "events": [], "stdout": text, "stderr": ""}
                row["usage"] = {"total_tokens": 0}
            else:
                agent = harness or {"dsh": DshHarness, "claude": ClaudeHarness, "codex": CodexHarness}[suite["harness"]]()
                if suite["harness"] == "dsh" and harness is None:
                    from .dsh import run_isolated
                    response = run_isolated(agent.binary, fixture["prompt"], work, base, kit,
                                            suite["model"], env, min(suite["timeout_s"], fixture["timeout_s"]))
                else:
                    response = agent.run(fixture["prompt"], work, env, min(suite["timeout_s"], fixture["timeout_s"]))
                text = response.text
                raw = {"text": text, "events": response.events, "stdout": response.raw_stdout,
                       "stderr": response.raw_stderr, "command": response.command}
                row["usage"] = normalized_usage(response.usage)
                row["agent_duration_s"] = response.duration_s
                if response.error:
                    row["status"] = ("timeout" if "timeout" in response.error.lower() else
                                     "auth-error" if any(t in response.error.lower() for t in ("auth", "401", "403")) else "harness-error")
                    row["error"] = response.error
            after = snapshot(work)
            artifact = store.redact({"raw": raw, "before": before, "after": after})
            artifact_hash = digest(artifact)
            store.write_once(f"artifacts/{row['id']}.json", artifact)
            row["artifact_hash"] = artifact_hash
            row["changed_files"] = changed(before, after)
            patch = "".join("".join(difflib.unified_diff(before.get(p, "").splitlines(True),
                                                       after.get(p, "").splitlines(True), fromfile="a/" + p, tofile="b/" + p))
                            for p in row["changed_files"])
            store.write_once(f"patches/{row['id']}.json", {"patch": patch})
            if row["error"]:
                return row
            row["assertions"] = _compliance(fixture, text, work, before, after, entry["variant"])
            kit_changed = [p for p in row["changed_files"] if p.startswith((".aiek/", ".agents/", ".claude/"))]
            row["assertions"].append(result("kit-files-preserved", not kit_changed, repr(kit_changed), dimension="safety", critical=True))
            outcome = fixture.get("outcome", {})
            kind = outcome.get("kind")
            if kind == "plus-email":
                configs = [p for p in row["changed_files"] if p.endswith((".toml", ".ini", ".cfg", ".yml", ".yaml", ".json"))]
                row["assertions"].append(result("configuration-preserved", not configs, repr(configs), dimension="safety", critical=True))
                row["assertions"].extend(grade_bug(fixture, work))
            elif kind == "signup-copy":
                row["assertions"].extend(grade_copy(fixture, work))
            elif kind == "human":
                source_changes = [p for p in row["changed_files"] if p in dict(fixture["setup"])]
                row["assertions"].append(result("input-source-preserved", not source_changes, repr(source_changes), critical=True))
                row["assertions"].append(human_outcome(fixture["id"], text, row["id"], artifact_hash))
            else:
                row["assertions"].append(result("outcome-unavailable", None, "Legacy fixture has no independent outcome grader"))
            row["status"] = "completed"
    except (ContractError, OSError, ValueError) as exc:
        message = str(exc)
        row["status"] = "install-error" if message.startswith("install-error:") else "grader-error"
        row["error"] = message
    finally:
        row["duration_s"] = round(time.monotonic() - started, 6)
    return row


def execute(suite: dict, fixtures: list[dict], kit: Path, store: EvidenceStore, *,
            dry_run: bool = False, resume: bool = False, harness=None) -> dict:
    validate_suite(suite, planning=dry_run)
    if store.manifest.get("suite") != suite:
        raise ContractError("suite does not match the experiment manifest")
    if store.manifest.get("fixtures") != {f["id"]: digest(f) for f in fixtures}:
        raise ContractError("fixtures do not match the experiment manifest")
    if suite["harness"] != "mock" and not dry_run:
        capabilities = store.manifest.get("harness", {}).get("capabilities", {})
        required = {"headless", "model_pinning", "global_config_isolation", "grader_isolation", "authentication"}
        required.update(suite.get("required_capabilities", []))
        missing = sorted(k for k in required if not capabilities.get(k))
        if missing:
            raise ContractError("live execution requires verified capabilities: " + ", ".join(missing))
    lookup = {f["id"]: f for f in fixtures}
    if set(suite["scenarios"]) - lookup.keys():
        raise ContractError("suite references unknown scenarios")
    trials = []
    with store.lock():
        stop = False
        for entry in schedule(suite):
            name = f"trials/{entry['id']}.json"
            path = store.root / name
            if path.exists():
                if not resume:
                    raise ContractError("experiment already has trials; use --resume or a new directory")
                row = json.loads(path.read_text())
            elif dry_run or stop:
                row = _record(entry, suite["harness"] == "mock")
            elif (store.root / f"trials/{entry['id']}.started.json").exists():
                row = _record(entry, suite["harness"] == "mock")
                row.update(status="interrupted", error="Previous attempt interrupted; not automatically retried")
                store.write_once(name, row)
            else:
                row = _trial(entry, lookup[entry["scenario"]], suite, kit, store, harness=harness)
                row = store.redact(row)
                validate("trial", row)
                store.write_once(name, row)
            trials.append(row)
            if row["status"] in ("auth-error", "install-error"):
                stop = True
        report = aggregate(trials, manifest=store.manifest)
        report["manifest"] = store.manifest
        report["trials"] = trials
        report["limitations"].extend(store.manifest.get("harness", {}).get("limitations", []))
        if not dry_run:
            name = f"reports/{digest(report)[:20]}.json"
            if not (store.root / name).exists():
                store.write_once(name, report)
        return report


def regrade(root: Path, labels: list[dict]) -> dict:
    saved = json.loads((root / "manifest.json").read_text())
    store = EvidenceStore(root, saved["inputs"])
    index = {label.get("trial_id"): label for label in labels}
    if len(index) != len(labels):
        raise ContractError("duplicate human labels")
    trials = []
    with store.lock():
        for entry in saved["inputs"]["schedule"]:
            path = root / f"trials/{entry['id']}.json"
            if not path.exists():
                raise ContractError("cannot regrade an unfinished experiment")
            row = json.loads(path.read_text())
            if row["id"] in index:
                artifact = json.loads((root / f"artifacts/{row['id']}.json").read_text())
                if digest(artifact) != row["artifact_hash"]:
                    raise ContractError("artifact integrity mismatch")
                matches = [a for a in row["assertions"] if a["id"] == "semantic-outcome"]
                if not matches:
                    raise ContractError("label supplied for a trial without a semantic grader")
                updated = human_outcome(row["scenario"], artifact["raw"]["text"], row["id"], row["artifact_hash"], index[row["id"]])
                row["assertions"] = [updated if a["id"] == "semantic-outcome" else a for a in row["assertions"]]
            trials.append(row)
        if set(index) - {r["id"] for r in trials}:
            raise ContractError("labels reference unknown trial IDs")
        report = aggregate(trials, manifest=saved["inputs"])
        report.update(manifest=saved["inputs"], trials=trials, label_hash=digest(labels))
        store.write_once(f"reports/regrade-{digest(report)[:20]}.json", report)
    return report


def blind_review(root: Path, report: dict) -> list[dict]:
    requests = []
    for row in report["trials"]:
        if any(a["status"] == "pending-review" for a in row["assertions"]):
            artifact = json.loads((root / f"artifacts/{row['id']}.json").read_text())
            requests.append({"trial_id": row["id"], "artifact_hash": row["artifact_hash"],
                             "rubric_version": f"{row['scenario']}/1", "response": artifact["raw"]["text"],
                             "passed": None, "reviewer": "", "evidence": ""})
    return requests
