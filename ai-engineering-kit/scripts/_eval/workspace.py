"""Fresh fixture workspaces and bounded, symlink-free snapshots."""
from __future__ import annotations

import os
from pathlib import Path

from .contracts import ContractError
from .process import run_process

EXCLUDED = {".git", "__pycache__", "node_modules", ".venv", ".isolated-agents-home"}
INSTALL_HARNESS = {"dsh": "codex", "codex": "codex", "claude": "claude", "mock": "codex"}


def safe_path(root: Path, relative: str) -> Path:
    name = Path(relative)
    if name.is_absolute() or not name.parts or any(p in ("..", ".git") for p in name.parts):
        raise ContractError(f"unsafe fixture path: {relative}")
    target = root / name
    if not target.resolve().is_relative_to(root.resolve()):
        raise ContractError(f"fixture path escapes workspace: {relative}")
    if any(p.is_symlink() for p in (target, *target.parents) if p != root.parent):
        # macOS /var is a system symlink; check only workspace descendants.
        current = root
        for part in name.parts:
            current = current / part
            if current.is_symlink():
                raise ContractError(f"symlink in workspace: {relative}")
    return target


def write_setup(root: Path, blocks: list) -> None:
    for name, content in blocks:
        path = safe_path(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")


def snapshot(root: Path, *, max_file: int = 1024 * 1024, max_total: int = 8 * 1024 * 1024) -> dict[str, str]:
    result = {}
    total = 0
    entries = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        entries += len(dirs) + len(files)
        if entries > 10000:
            raise ContractError("workspace evidence exceeds entry limit")
        for name in list(dirs):
            path = Path(directory) / name
            if path.is_symlink():
                raise ContractError(f"symlink directory: {path.relative_to(root)}")
            if name in EXCLUDED:
                dirs.remove(name)
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                raise ContractError(f"non-regular file: {path.relative_to(root)}")
            size = path.stat().st_size
            total += size
            if size > max_file or total > max_total:
                raise ContractError("workspace evidence exceeds size limit")
            try:
                result[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
            except UnicodeError as exc:
                raise ContractError(f"binary evidence unsupported: {path.relative_to(root)}") from exc
    return result


def changed(before: dict, after: dict) -> list[str]:
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


def install(kit: Path, root: Path, harness: str, profile: str = "full") -> dict:
    command = ["bash", str(kit / "scripts/install.sh"), str(root), "--harness", INSTALL_HARNESS[harness], "--profile", profile]
    rc, out, err, duration, _ = run_process(command, cwd=kit, timeout=180)
    if rc != 0:
        raise ContractError(f"install-error: installer exited {rc}: {err[-400:]}")
    return {"command": ["bash", "scripts/install.sh", "<workspace>", "--harness", INSTALL_HARNESS[harness], "--profile", profile],
            "profile": profile, "returncode": rc, "duration_s": duration, "planner_installed": False,
            "skills": sorted(p.parent.name for p in root.glob(".*/skills/*/SKILL.md"))}


def commit_baseline(root: Path) -> str:
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    commands = [["git", "add", "-A"],
                ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgSign=false",
                 "-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "-q", "-m", "fixture baseline"],
                ["git", "rev-parse", "HEAD"]]
    for command in commands:
        rc, out, err, _, _ = run_process(command, cwd=root, timeout=30, env=env)
        if rc != 0:
            raise ContractError("harness-error: fixture baseline commit failed: " + err[-200:])
    return out.strip()


def prepare_env(config_root: Path, harness: str, profile: str = "full") -> dict:
    env = dict(os.environ)
    agents = config_root / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    env["DSH_AGENTS_HOME"] = str(agents)
    # Existing CLI authentication stays with its owner. Global isolation is NOT
    # certified merely because the global agents directory is redirected.
    return env
