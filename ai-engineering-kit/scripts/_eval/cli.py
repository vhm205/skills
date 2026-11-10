"""Version 2 command adapter. Legacy parsing stays at the public entry point."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import uuid

from .contracts import ContractError, validate_suite
from .harnesses import describe
from .reporting import markdown_report
from .runner import EvidenceStore, blind_review, execute, make_manifest, regrade


def _emit(args, report: dict) -> None:
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    for path in (args.out, args.benchmark):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            path.with_suffix(".md").write_text(markdown_report(report) if "variants" in report else content)
    if args.json:
        print(content, end="")


def run(args) -> int:
    import eval_tasks
    try:
        evidence_root = args.regrade or args.experiment_dir
        if evidence_root:
            for output in (args.out, args.benchmark):
                if output and output.resolve().is_relative_to(evidence_root.resolve()):
                    raise ContractError("--out/--benchmark must be outside the immutable experiment directory")
        if args.regrade:
            if not args.labels:
                raise ContractError("--regrade requires --labels; no agent will be called")
            report = regrade(args.regrade.resolve(), json.loads(args.labels.read_text()))
            _emit(args, report)
            print("Regraded evidence; original trials preserved.", file=sys.stderr)
            return 0
        if args.labels:
            raise ContractError("--labels is only valid with --regrade")
        if args.resume and not args.experiment_dir:
            raise ContractError("--resume requires --experiment-dir")
        kit = args.kit_root.resolve()
        all_fixtures = eval_tasks.load_fixtures((args.tasks_dir or kit / "evals/tasks").resolve())
        if args.list:
            for fixture in all_fixtures:
                print(f"{fixture['id']:<16} {fixture['title']} (fixture v{fixture['version']})")
            return 0
        if args.suite:
            suite = json.loads(args.suite.read_text())
            if args.mock:
                suite["harness"] = "mock"
            elif args.harness != "auto":
                suite["harness"] = args.harness
            if args.model:
                suite["model"] = args.model
            if args.max_trials is not None:
                suite["max_trials"] = args.max_trials
        else:
            scenarios = [item.strip() for arg in args.scenario or [] for item in arg.split(",") if item.strip()]
            scenarios = scenarios or [f["id"] for f in all_fixtures]
            variants = ["no-kit", "full-kit"] if args.both else ["no-kit" if args.without_skill else "full-kit"]
            suite = {"schema": "aiek-eval-suite/2", "id": "behavior", "harness": "mock" if args.mock else args.harness,
                     "model": args.model, "scenarios": scenarios, "variants": variants,
                     "repeats": args.runs, "max_trials": args.max_trials if args.max_trials is not None else len(scenarios)*len(variants)*args.runs,
                     "timeout_s": args.timeout, "seed": args.seed}
        if suite["harness"] == "auto":
            # Explicit selection is required for comparable real experiments.
            raise ContractError("v2 requires --harness dsh|claude|codex or --mock; no auto fallback")
        validate_suite(suite, planning=args.dry_run or args.preflight)
        lookup = {f["id"]: f for f in all_fixtures}
        if set(suite["scenarios"]) - lookup.keys():
            raise ContractError("suite references unknown scenarios")
        fixtures = [lookup[name] for name in suite["scenarios"]]
        info = ({"name": "mock", "version": "synthetic/2", "capabilities": {},
                 "limitations": ["Synthetic plumbing only; no agent performance evidence."]}
                if suite["harness"] == "mock" else describe(suite["harness"]))
        required = set(suite.get("required_capabilities", []))
        if suite["harness"] != "mock":
            required |= {"headless", "model_pinning", "global_config_isolation", "grader_isolation", "authentication"}
        missing = sorted(k for k in required if not info["capabilities"].get(k)) if suite["harness"] != "mock" else []
        if suite["harness"] != "mock" and not suite.get("model"):
            missing.append("model_selection")
        if args.preflight:
            report = {"schema": "aiek-eval-preflight/2", "status": "unsupported" if missing else "ready",
                      "harness": info, "model_requested": suite["model"], "missing_capabilities": missing,
                      "agent_calls": 0}
            _emit(args, report)
            print(json.dumps(report), file=sys.stderr)
            return 2 if missing else 0
        if missing and not args.dry_run:
            raise ContractError("live evaluation blocked; missing verified capabilities: " + ", ".join(missing) +
                                ". Use --preflight for evidence; no agent calls were made.")
        directory = (args.experiment_dir or kit / "evals/results/local" /
                     (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])).resolve()
        secrets = [value for key, value in os.environ.items()
                   if any(token in key.upper() for token in ("KEY", "TOKEN", "SECRET", "PASSWORD"))]
        store = EvidenceStore(directory, make_manifest(suite, fixtures, kit, info), secrets=secrets)
        report = execute(suite, fixtures, kit, store, dry_run=args.dry_run, resume=args.resume)
        if not args.dry_run:
            requests = blind_review(directory, report)
            if requests:
                from .contracts import digest
                review_name = f"reviews/request-{digest(requests)[:20]}.json"
                if not (directory / review_name).exists():
                    store.write_once(review_name, requests)
        _emit(args, report)
        print(f"Eval v2: {len(report['trials'])} trials; synthetic={report['synthetic']}; evidence={directory}", file=sys.stderr)
        if args.dry_run:
            print("Planned only; no agent calls or scored successes.", file=sys.stderr)
            return 0
        target = report["variants"].get("full-kit") or next(iter(report["variants"].values()))
        if any(s["errors"] for s in report["variants"].values()):
            return 2
        if target["critical_violations"]:
            return 1
        if suite["harness"] == "mock":
            print("Offline plumbing completed; unavailable/pending outcomes are NOT a model pass.", file=sys.stderr)
            return 0
        if target["coverage"] != 1:
            return 3
        return 0 if target["quality_rate"] >= args.fail_below else 1
    except (ContractError, eval_tasks.FixtureError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Eval configuration/evidence error: {exc}", file=sys.stderr)
        return 2
