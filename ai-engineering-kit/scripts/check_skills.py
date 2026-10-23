#!/usr/bin/env python3
"""Validate Agent Skills directories (kit repo or an installed project).

Checks the parts of the Agent Skills contract that a static check can prove:

- every skill is a directory with exactly ``SKILL.md`` (case-sensitive);
- frontmatter exists, contains only ``name`` and ``description`` (kit policy),
  ``name`` matches the directory and the lowercase-hyphenated format,
  ``description`` is non-empty and <= 1024 characters;
- the body stays within the size budget (warn over --target-body, fail over --max-body);
- ``references/...`` files, relative Markdown links, and ``.aiek/core`` /
  ``.aiek/scripts`` references exist;
- when both ``.agents/skills`` and ``.claude/skills`` exist, they are in parity.

Exit codes: 0 = pass (warnings allowed), 1 = violations, 2 = usage error.
No third-party dependencies: it must run in a project that only installed the kit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`]+)`")
AIEK_CORE_RE = re.compile(r"\.aiek/core/([A-Za-z0-9_.-]+\.md)")
AIEK_SCRIPTS_RE = re.compile(r"\.aiek/scripts/([A-Za-z0-9_.-]+\.py)")
ALLOWED_FIELDS = {"name", "description"}
IGNORED_DIRS = {"node_modules", ".git", "dist", "coverage", "test-results",
                "playwright-report", "__pycache__", ".worktrees"}


class FrontmatterError(ValueError):
    pass


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse a small, safe subset of YAML frontmatter (top-level scalars only)."""
    if not text.startswith("---"):
        raise FrontmatterError("missing frontmatter (file must start with '---')")
    lines = text.splitlines()
    if lines[0].strip() != "---":
        raise FrontmatterError("first line must be '---'")
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        raise FrontmatterError("unterminated frontmatter (missing closing '---')")
    fields: dict[str, str] = {}
    line_no = 1
    while line_no < end:
        raw = lines[line_no]
        if not raw.strip():
            line_no += 1
            continue
        if raw.startswith((" ", "\t")):
            raise FrontmatterError(
                f"unexpected indentation at frontmatter line {line_no + 1}; "
                "kit skills use plain top-level scalars")
        if ":" not in raw:
            raise FrontmatterError(
                f"expected 'key: value' at frontmatter line {line_no + 1}")
        key, value = raw.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key:
            raise FrontmatterError(f"empty key at frontmatter line {line_no + 1}")
        if key in fields:
            raise FrontmatterError(f"duplicate frontmatter key '{key}'")
        if value in {"|", ">", "|-", ">-"}:
            block: list[str] = []
            line_no += 1
            while line_no < end:
                block_line = lines[line_no]
                if block_line.strip() and not block_line.startswith((" ", "\t")):
                    break
                block.append(block_line.strip())
                line_no += 1
            separator = "\n" if value.startswith("|") else " "
            fields[key] = separator.join(part for part in block if part).strip()
            continue
        fields[key] = _unquote(value)
        line_no += 1
    body = "\n".join(lines[end + 1:])
    return fields, body


class Skill:
    def __init__(self, path: Path, root: Path, project: Path):
        self.path = path
        self.root = root
        self.project = project
        self.name = path.parent.name
        self.fields: dict[str, str] = {}
        self.body = ""
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def rel(self) -> str:
        try:
            return str(self.path.relative_to(self.project))
        except ValueError:
            return str(self.path)

    def error(self, message: str) -> None:
        self.errors.append(f"{self.rel}: {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(f"{self.rel}: {message}")

    def load(self) -> None:
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            self.error(f"cannot read file: {exc}")
            return
        try:
            self.fields, self.body = parse_frontmatter(text)
        except FrontmatterError as exc:
            self.error(str(exc))
            return
        self._check_metadata()
        self._check_body()
        self._check_links()

    def _check_metadata(self) -> None:
        unknown = sorted(set(self.fields) - ALLOWED_FIELDS)
        if unknown:
            self.error(
                "frontmatter must contain only name and description; unknown: "
                + ", ".join(unknown))
        name = self.fields.get("name")
        description = self.fields.get("description")
        if not isinstance(name, str) or not name.strip():
            self.error("missing name")
        elif not NAME_RE.fullmatch(name):
            self.error(f"invalid name '{name}' (use lowercase-hyphenated)")
        elif name != self.name:
            self.error(f"name '{name}' must equal the directory name '{self.name}'")
        if not isinstance(description, str) or not description.strip():
            self.error("missing description")
        elif len(description) > 1024:
            self.error(f"description is {len(description)} chars (max 1024)")

    def _check_body(self) -> None:
        lines = self.body.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        count = len(lines)
        if count > self.args_max_body:
            self.error(f"body is {count} lines (max {self.args_max_body})")
        elif count > self.args_target_body:
            self.warn(
                f"body is {count} lines (target <= {self.args_target_body}); "
                "move detail to references/")

    def _check_links(self) -> None:
        for ref in BACKTICK_RE.findall(self.body):
            ref = ref.strip()
            if ref.startswith("<") or ref.startswith("http"):
                continue
            if ref.startswith("references/"):
                self._require_file(ref, f"reference '{ref}' does not exist")
        for target in LINK_RE.findall(self.body):
            target = target.strip()
            if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#|/|<)", target):
                continue
            target = target.split("#", 1)[0].split("?", 1)[0]
            if target:
                self._require_file(target, f"link '{target}' does not exist")
        for name in AIEK_CORE_RE.findall(self.body):
            candidates = [self.project / ".aiek/core" / name]
            if self.kit:
                candidates.append(self.kit / "core" / name)
            if not any(candidate.is_file() for candidate in candidates):
                self.error(f"core link '.aiek/core/{name}' does not exist")
        for name in AIEK_SCRIPTS_RE.findall(self.body):
            candidates = [self.project / ".aiek/scripts" / name]
            if self.kit:
                candidates.append(self.kit / "scripts" / name)
            if not any(candidate.is_file() for candidate in candidates):
                self.error(f"script link '.aiek/scripts/{name}' does not exist")

    def _require_file(self, ref: str, message: str) -> None:
        target = (self.path.parent / ref).resolve()
        try:
            target.relative_to(self.project.resolve())
        except ValueError:
            self.error(f"reference escapes the project: '{ref}'")
            return
        if not target.is_file():
            self.error(message)

    def digest(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def as_dict(self) -> dict:
        return {
            "path": self.rel,
            "name": self.name,
            "description_chars": len(self.fields.get("description", "") or ""),
            "body_lines": len(self.body.splitlines()),
            "errors": self.errors,
            "warnings": self.warnings,
        }


def discover_roots(paths: list[Path]) -> list[Path]:
    roots: list[Path] = []
    for path in paths:
        path = path.resolve()
        if not path.exists():
            raise SystemExit(f"error: path not found: {path}")
        candidates: list[Path] = []
        for rel in (".agents/skills", ".claude/skills", "skills"):
            candidate = path / rel
            if candidate.is_dir():
                candidates.append(candidate)
        if not candidates and (path / "SKILL.md").is_file():
            candidates.append(path.parent)
        if not candidates:
            # A bare skills root: direct children that are skill directories.
            if any((child / "SKILL.md").is_file() for child in path.iterdir() if child.is_dir()):
                candidates.append(path)
        for candidate in candidates:
            if candidate not in roots:
                roots.append(candidate)
    if not roots:
        raise SystemExit("error: no skills directory found "
                         "(looked for skills/, .agents/skills, .claude/skills)")
    return roots


def find_case_errors(root: Path, project: Path, errors: list[str]) -> None:
    for path in root.rglob("*.md"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.name.lower() == "skill.md" and path.name != "SKILL.md":
            errors.append(
                f"{path.relative_to(project)}: skill entry must be named exactly "
                "'SKILL.md' (case-sensitive)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Agent Skills directories (metadata, size, links, parity).",
        epilog="Examples: check_skills.py .  |  check_skills.py /path/project --kit /path/kit")
    parser.add_argument("paths", nargs="*", default=["."],
                        help="project root, skills root, or installed project (default: .)")
    parser.add_argument("--kit", type=Path, default=None,
                        help="kit checkout, used to resolve .aiek/core and .aiek/scripts links")
    parser.add_argument("--canonical", choices=[".agents", ".claude"], default=".agents",
                        help="canonical skills root when both exist (default: .agents)")
    parser.add_argument("--require-trigger", action="store_true",
                        help="require descriptions to contain 'Use when' and 'Not for'")
    parser.add_argument("--target-body", type=int, default=120,
                        help="warn above this many body lines (default: 120)")
    parser.add_argument("--max-body", type=int, default=250,
                        help="fail above this many body lines (default: 250)")
    parser.add_argument("--allow-warnings", action="store_true",
                        help="exit 0 even when warnings were reported (default: 0 anyway)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    if args.kit is not None:
        args.kit = args.kit.resolve()
        if not args.kit.is_dir():
            parser.error(f"--kit is not a directory: {args.kit}")
    try:
        roots = discover_roots([Path(p) for p in args.paths])
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    skills: list[Skill] = []
    root_info: list[dict] = []

    for root in roots:
        if root.name == "skills" and root.parent.name in {".agents", ".claude"}:
            project = root.parent.parent
        elif root.name == "skills":
            project = root.parent
        else:
            project = root
        find_case_errors(root, project, errors)
        entries = [child for child in root.iterdir() if child.is_dir()]
        found = 0
        for child in entries:
            if child.name in IGNORED_DIRS:
                continue
            skill_file = child / "SKILL.md"
            if not skill_file.is_file():
                errors.append(f"{skill_file.relative_to(project)}: missing")
                continue
            found += 1
            skill = Skill(skill_file, root, project)
            skill.kit = args.kit
            skill.args_max_body = args.max_body
            skill.args_target_body = args.target_body
            skill.load()
            if args.require_trigger:
                description = skill.fields.get("description", "") or ""
                if description:
                    if "use when" not in description.lower():
                        skill.error("description must contain 'Use when'")
                    if "not for" not in description.lower():
                        skill.error("description must contain 'Not for'")
            skills.extend([skill])
            errors.extend(skill.errors)
            warnings.extend(skill.warnings)
        root_info.append({"root": str(root), "skills": found})

    # Parity between installed roots (D4: .agents is canonical, .claude is a mirror).
    by_root: dict[Path, dict[str, Skill]] = {}
    for skill in skills:
        by_root.setdefault(skill.root, {})[skill.name] = skill
    canonical_name = args.canonical
    canonical_roots = [root for root in roots if root.parent.name == canonical_name]
    mirror_roots = [root for root in roots if root.parent.name != canonical_name]
    for canonical_root in canonical_roots:
        canonical = by_root[canonical_root]
        for mirror_root in mirror_roots:
            mirror = by_root[mirror_root]
            mirror_rel = mirror_root.relative_to(mirror_root.parent.parent)
            for name in sorted(set(canonical) - set(mirror)):
                errors.append(
                    f"{mirror_rel}: missing skill "
                    f"'{name}' (canonical source: {canonical_name})")
            for name in sorted(set(mirror) - set(canonical)):
                errors.append(
                    f"{mirror_rel}: unexpected skill "
                    f"'{name}' not present in canonical {canonical_name}")
            for name in sorted(set(canonical) & set(mirror)):
                if canonical[name].digest() != mirror[name].digest():
                    errors.append(
                        f"{mirror[name].rel}: differs from canonical "
                        f"{canonical[name].rel} ({canonical_name})")

    payload = {
        "ok": not errors,
        "roots": root_info,
        "skills": len(skills),
        "errors": errors,
        "warnings": warnings,
        "details": [skill.as_dict() for skill in skills],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for message in errors:
            print("FAIL " + message)
        for message in warnings:
            print("warn " + message)
        if errors:
            print(f"FAIL: {len(errors)} violation(s) across {len(skills)} skill(s)")
        else:
            print(f"OK: {len(skills)} skills; metadata, size, links and parity consistent"
                  + (f" ({len(warnings)} warning(s))" if warnings else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
