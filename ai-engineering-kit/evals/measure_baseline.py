#!/usr/bin/env python3
"""Measure static baseline metrics for the AI Engineering Kit.

Usage:
    python3 evals/measure_baseline.py --kit-root /tmp/aiek-baseline/ai-engineering-kit
    python3 evals/measure_baseline.py --kit-root . --format markdown

Metrics per skill: description length, whether the description contains a literal
"Use when" trigger, a negative trigger ("Not for", "excludes", ...), quoted trigger
examples, body lines/chars (frontmatter excluded), and reference file count. The
aggregate also counts skill-local scripts and whether an evals/ directory exists.

No third-party dependencies; no network; read-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

USE_WHEN_RE = re.compile(r"\buse when\b", re.I)
NEGATIVE_RE = re.compile(
    r"\b(not\s+for|not\s+used\s+for|do\s+not\s+use|don't\s+use|excludes?|excluded?|"
    r"not\s+a\s+substitute|instead\s+use)\b",
    re.I,
)
EXAMPLE_RE = re.compile(r"""['"][^'"]{4,120}['"]""")
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)


def parse_description(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return ""
    lines = match.group(1).splitlines()
    for index, line in enumerate(lines):
        value_match = re.match(r"^description\s*:\s*(.*)$", line)
        if not value_match:
            continue
        value = value_match.group(1).strip()
        if value in ("|", ">", "|-", ">-"):
            collected: list[str] = []
            for block_line in lines[index + 1:]:
                if block_line.strip() and not block_line.startswith((" ", "\t")):
                    break
                collected.append(block_line.strip())
            return re.sub(r"\s+", " ", " ".join(collected)).strip()
        return re.sub(r"\s+", " ", value.strip().strip("\"'")).strip()
    return ""


def measure(kit_root: Path) -> dict:
    skills_dir = kit_root / "skills"
    skill_dirs = sorted(path for path in skills_dir.iterdir() if (path / "SKILL.md").is_file())
    rows: list[dict] = []
    totals = {
        "skills": len(skill_dirs),
        "with_use_when": 0,
        "with_negative_trigger": 0,
        "with_trigger_examples": 0,
        "description_chars": 0,
        "body_lines": 0,
        "body_chars": 0,
        "reference_files": 0,
        "skill_scripts": len(list(skills_dir.glob("*/scripts/*"))),
        "has_evals_dir": (kit_root / "evals").is_dir(),
        "has_trigger_json": (kit_root / "evals" / "trigger.json").is_file(),
    }
    for skill_dir in skill_dirs:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        description = parse_description(text)
        body = FRONTMATTER_RE.sub("", text, count=1)
        references_dir = skill_dir / "references"
        reference_files = len([path for path in references_dir.iterdir() if path.is_file()]) if references_dir.is_dir() else 0
        row = {
            "skill": skill_dir.name,
            "description_chars": len(description),
            "body_lines": len(body.splitlines()),
            "body_chars": len(body),
            "use_when": bool(USE_WHEN_RE.search(description)),
            "negative_trigger": bool(NEGATIVE_RE.search(description)),
            "trigger_examples": bool(EXAMPLE_RE.search(description)),
            "reference_files": reference_files,
        }
        rows.append(row)
        totals["with_use_when"] += row["use_when"]
        totals["with_negative_trigger"] += row["negative_trigger"]
        totals["with_trigger_examples"] += row["trigger_examples"]
        totals["description_chars"] += row["description_chars"]
        totals["body_lines"] += row["body_lines"]
        totals["body_chars"] += row["body_chars"]
        totals["reference_files"] += row["reference_files"]
    if not rows:
        raise SystemExit(f"error: no skills found under {skills_dir}")
    return {"kit_root": str(kit_root), "totals": totals, "skills": rows}


def to_markdown(data: dict) -> str:
    totals = data["totals"]
    lines = [
        f"Kit root: `{data['kit_root']}`",
        "",
        "| Skill | Description chars | Use when | Negative trigger | Trigger examples | Body lines | Refs |",
        "|---|---:|:---:|:---:|:---:|---:|---:|",
    ]
    for row in data["skills"]:
        lines.append(
            f"| `{row['skill']}` | {row['description_chars']} | "
            f"{'yes' if row['use_when'] else 'no'} | {'yes' if row['negative_trigger'] else 'no'} | "
            f"{'yes' if row['trigger_examples'] else 'no'} | {row['body_lines']} | {row['reference_files']} |"
        )
    lines += [
        "",
        f"Totals: {totals['skills']} skills; `Use when` {totals['with_use_when']}/{totals['skills']}; "
        f"negative trigger {totals['with_negative_trigger']}/{totals['skills']}; "
        f"quoted trigger examples {totals['with_trigger_examples']}/{totals['skills']}; "
        f"description {totals['description_chars']} chars; body {totals['body_lines']} lines / "
        f"{totals['body_chars']} chars; {totals['reference_files']} reference files; "
        f"{totals['skill_scripts']} skill-local script files; evals/={totals['has_evals_dir']}; "
        f"trigger.json={totals['has_trigger_json']}.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Static baseline metrics for the AI Engineering Kit.")
    parser.add_argument("--kit-root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="kit checkout to measure (default: this repository's kit)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args(argv)
    if not (args.kit_root / "skills").is_dir():
        print(f"error: not a kit root (no skills/): {args.kit_root}", file=sys.stderr)
        return 2
    data = measure(args.kit_root.resolve())
    if args.format == "markdown":
        print(to_markdown(data))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
