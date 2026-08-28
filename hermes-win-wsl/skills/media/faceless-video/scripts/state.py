#!/usr/bin/env python3
"""Durable state helper for the faceless-video Hermes skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATES = {
    "input_analysis",
    "asset_planning",
    "researching",
    "building_structure",
    "structure_review",
    "writing_script",
    "script_review",
    "building_hyperframes",
    "visual_verification",
    "generating_voice",
    "syncing_timeline",
    "syncing_subtitles",
    "qa",
    "video_review",
    "revising",
    "completed",
}
GATES = {"structure", "script", "video"}
LOCK_KINDS = {"structure", "script"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_path(project: Path) -> Path:
    return project / "production" / "state.json"


def load(project: Path) -> dict[str, Any]:
    path = state_path(project)
    if not path.is_file():
        raise SystemExit(f"State file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read state: {exc}") from exc
    validate_data(data)
    return data


def save(project: Path, data: dict[str, Any]) -> None:
    path = state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate_data(data: dict[str, Any]) -> None:
    if data.get("schema_version") != 1:
        raise SystemExit("Unsupported or missing state schema_version")
    if data.get("state") not in STATES:
        raise SystemExit(f"Invalid workflow state: {data.get('state')!r}")
    gates = data.get("gates")
    if not isinstance(gates, dict) or set(gates) != GATES:
        raise SystemExit("State must contain exactly structure, script, and video gates")
    for name, gate in gates.items():
        if gate.get("status") not in {"pending", "approved"}:
            raise SystemExit(f"Invalid gate status for {name}")
    locks = data.get("locks", {})
    if not isinstance(locks, dict) or not set(locks).issubset(LOCK_KINDS):
        raise SystemExit("Invalid artifact locks")


def digest(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Artifact not found: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_to_project(project: Path, artifact: Path) -> str:
    try:
        return artifact.resolve().relative_to(project.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit("Locked artifacts must be inside the project workspace") from exc


def command_init(args: argparse.Namespace) -> None:
    project = Path(args.project)
    path = state_path(project)
    if path.exists() and not args.force:
        raise SystemExit(f"State already exists: {path}; use --force only to reset intentionally")
    for directory in (
        "input",
        "editorial",
        "assets",
        "audio",
        "production/hyperframes",
        "preview",
        "output",
    ):
        (project / directory).mkdir(parents=True, exist_ok=True)
    timestamp = now()
    data = {
        "schema_version": 1,
        "workflow": "faceless-video",
        "state": "input_analysis",
        "created_at": timestamp,
        "updated_at": timestamp,
        "input": {
            "topic": args.topic,
            "target_audience": args.audience,
            "target_duration": args.duration,
            "voice_reference": args.voice_reference,
        },
        "defaults": {
            "narration_language": "Vietnamese",
            "subtitle_language": "English",
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "voice_engine": "OmniVoice",
            "editorial_model": "GPT-5.6 Sol",
            "production_model": "Claude Opus",
            "hyperframes_skill": "/faceless-explainer",
        },
        "gates": {name: {"status": "pending", "approved_at": None} for name in sorted(GATES)},
        "locks": {},
        "history": [{"at": timestamp, "event": "initialized", "state": "input_analysis"}],
    }
    save(project, data)
    print(path)


def command_show(args: argparse.Namespace) -> None:
    print(json.dumps(load(Path(args.project)), ensure_ascii=False, indent=2))


def command_transition(args: argparse.Namespace) -> None:
    if args.state not in STATES:
        raise SystemExit(f"Unknown state: {args.state}")
    project = Path(args.project)
    data = load(project)
    previous = data["state"]
    timestamp = now()
    data["state"] = args.state
    data["updated_at"] = timestamp
    event = {"at": timestamp, "event": "transition", "from": previous, "to": args.state}
    if args.note:
        event["note"] = args.note
    data["history"].append(event)
    save(project, data)
    print(args.state)


def command_approve(args: argparse.Namespace) -> None:
    if args.gate not in GATES:
        raise SystemExit(f"Unknown gate: {args.gate}")
    project = Path(args.project)
    data = load(project)
    timestamp = now()
    data["gates"][args.gate] = {"status": "approved", "approved_at": timestamp}
    data["updated_at"] = timestamp
    data["history"].append({"at": timestamp, "event": "gate_approved", "gate": args.gate})
    save(project, data)
    print(args.gate)


def command_lock(args: argparse.Namespace) -> None:
    if args.kind not in LOCK_KINDS:
        raise SystemExit(f"Unknown lock kind: {args.kind}")
    project = Path(args.project)
    artifact = Path(args.file)
    if not artifact.is_absolute():
        artifact = project / artifact
    data = load(project)
    timestamp = now()
    lock = {
        "path": relative_to_project(project, artifact),
        "sha256": digest(artifact),
        "locked_at": timestamp,
    }
    data["locks"][args.kind] = lock
    data["updated_at"] = timestamp
    data["history"].append({"at": timestamp, "event": "artifact_locked", "kind": args.kind, **lock})
    save(project, data)
    print(lock["sha256"])


def verify_locks(project: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for kind, lock in data["locks"].items():
        artifact = project / lock["path"]
        if not artifact.is_file():
            errors.append(f"{kind}: missing {artifact}")
            continue
        actual = digest(artifact)
        if actual != lock["sha256"]:
            errors.append(f"{kind}: hash mismatch for {artifact}")
    return errors


def command_verify(args: argparse.Namespace) -> None:
    project = Path(args.project)
    data = load(project)
    errors = verify_locks(project, data)
    if args.require_all_locks:
        missing = LOCK_KINDS - set(data["locks"])
        errors.extend(f"missing lock: {kind}" for kind in sorted(missing))
    if args.require_all_gates:
        pending = [name for name, gate in data["gates"].items() if gate["status"] != "approved"]
        errors.extend(f"pending gate: {name}" for name in pending)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print("ok")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--project", required=True)
    init.add_argument("--topic", required=True)
    init.add_argument("--audience", required=True)
    init.add_argument("--duration", required=True)
    init.add_argument("--voice-reference", default=None)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    show = commands.add_parser("show")
    show.add_argument("--project", required=True)
    show.set_defaults(func=command_show)

    transition = commands.add_parser("transition")
    transition.add_argument("--project", required=True)
    transition.add_argument("--state", required=True, choices=sorted(STATES))
    transition.add_argument("--note")
    transition.set_defaults(func=command_transition)

    approve = commands.add_parser("approve")
    approve.add_argument("--project", required=True)
    approve.add_argument("--gate", required=True, choices=sorted(GATES))
    approve.set_defaults(func=command_approve)

    lock = commands.add_parser("lock")
    lock.add_argument("--project", required=True)
    lock.add_argument("--kind", required=True, choices=sorted(LOCK_KINDS))
    lock.add_argument("--file", required=True)
    lock.set_defaults(func=command_lock)

    verify = commands.add_parser("verify")
    verify.add_argument("--project", required=True)
    verify.add_argument("--require-all-locks", action="store_true")
    verify.add_argument("--require-all-gates", action="store_true")
    verify.set_defaults(func=command_verify)
    return root


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
