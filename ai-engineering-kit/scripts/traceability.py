#!/usr/bin/env python3
"""Check that acceptance/success criteria are traceable to rows, tasks and proof.

Reads a Markdown spec/plan/tasks document (read-only) and validates:

* every criterion has a stable label under "Acceptance Criteria" or Spec Kit's
  "Success Criteria": ``AC-<id>`` (acceptance) or ``SC-<id>`` (success criteria, the
  default ``spec.md`` template convention),
* labels are not duplicated,
* every traceability row references a defined criterion and carries proof,
* criteria have a traceability row (or task reference) — always enforced when a
  traceability table is present, and otherwise only with ``--require-rows`` so a plain
  upstream ``spec.md`` is not reported as broken.

The output names the file and line for every problem and says what to add, so it can be
used by ``intaking-ticket`` right after the traceability table is written.

Exit codes: 0 = traceable, 1 = problems found (or unreadable file), 2 = bad usage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
CHECKBOX_RE = re.compile(r"^\[[ xX]\]\s*(.*)$")
CRITERION_ID_RE = re.compile(r"\b(AC|SC)(?:[-_ ]([A-Za-z0-9]+)|(\d+[A-Za-z0-9]*))\b")
BARE_ID_RE = re.compile(r"^[A-Za-z]?\d+[A-Za-z0-9]*$")

AC_HEADING_WORDS = (
    "acceptance",
    "definition of done",
    "success criteria",
    "what success",
    "tiêu chí",
    "nghiệm thu",
)
TRACE_HEADING_WORDS = ("traceab", "traceability", "coverage")

AC_HEADER_WORDS = {
    "ac",
    "ac id",
    "acs",
    "id",
    "acceptance",
    "acceptance criteria",
    "acceptance criterion",
    "criterion",
    "criteria",
    "requirement",
    "req",
    "requirements",
}
PROOF_HEADER_WORDS = (
    "proof",
    "proven",
    "proven by",
    "how proven",
    "how to prove",
    "verification method",
    "evidence",
    "verification",
    "verified by",
    "verify",
    "test",
    "tests",
    "check",
    "command",
    "artifact",
    "how verified",
)
TASK_HEADER_WORDS = ("task", "tasks", "implementation", "work", "change", "deliverable")
ACCEPTANCE_CASE_WORDS = ("acceptance case", "acceptance", "case", "uat", "scenario")
PLACEHOLDERS = {"", "-", "--", "---", "—", "–", "n/a", "na", "tbd", "todo", "pending", "?", "none", "x"}


class Problem(dict):
    def __init__(self, code, message, line=None, severity="error"):
        super().__init__(code=code, message=message, line=line, severity=severity)


def canonical_id(match):
    prefix = match.group(1).upper()
    identifier = match.group(2) or match.group(3) or ""
    identifier = identifier.strip().upper()
    return "%s-%s" % (prefix, identifier) if identifier else None


def ids_in(text):
    return [
        identifier
        for identifier in (canonical_id(m) for m in CRITERION_ID_RE.finditer(text))
        if identifier
    ]


def _split_row(line):
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    cells = re.split(r"(?<!\\)\|", text)
    return [cell.strip().replace("\\|", "|") for cell in cells]


def _is_separator(line):
    stripped = line.strip()
    if "-" not in stripped:
        return False
    if not re.fullmatch(r"[\s|:-]+", stripped):
        return False
    return bool(re.search(r"-{2,}", stripped))


def _tables(lines):
    """Return markdown tables as dicts with 1-based header/row line numbers."""
    tables = []
    index = 0
    while index < len(lines) - 1:
        if lines[index].strip().startswith("|") and _is_separator(lines[index + 1]):
            header = _split_row(lines[index])
            rows = []
            cursor = index + 2
            while cursor < len(lines) and lines[cursor].strip().startswith("|"):
                rows.append((cursor + 1, _split_row(lines[cursor])))
                cursor += 1
            tables.append(
                {
                    "header_line": index + 1,
                    "header": header,
                    "rows": rows,
                    "start": index,
                    "end": cursor,
                }
            )
            index = cursor
        else:
            index += 1
    return tables


def _headings(lines):
    headings = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    return headings


def _criterion_sections(lines):
    """Return ``[(start, end, heading_lower)]`` for Acceptance/Success Criteria sections."""
    headings = _headings(lines)
    sections = []
    for position, (index, level, text) in enumerate(headings):
        lowered = text.lower()
        if not any(word in lowered for word in AC_HEADING_WORDS):
            continue
        end = len(lines)
        for other_index, other_level, _other_text in headings[position + 1 :]:
            if other_level <= level:
                end = other_index
                break
        sections.append((index + 1, end, lowered))  # 0-based, heading line excluded
    return sections


def _column(header, words):
    for index, cell in enumerate(header):
        lowered = re.sub(r"[*_`]", "", cell).strip().lower()
        if lowered in words:
            return index
    for index, cell in enumerate(header):
        lowered = re.sub(r"[*_`]", "", cell).strip().lower()
        if any(word in lowered for word in words if len(word) > 3):
            return index
    return None


def _ac_column(table):
    column = _column(table["header"], AC_HEADER_WORDS)
    if column is not None:
        return column
    # Header-less or renamed column: find a column that mostly holds AC ids / ids.
    width = len(table["header"])
    best = None
    for candidate in range(width):
        values = [cells[candidate] for _line, cells in table["rows"] if candidate < len(cells)]
        if not values:
            continue
        matches = sum(1 for value in values if ids_in(value) or BARE_ID_RE.match(value.strip()))
        if matches and matches >= max(1, len(values) // 2):
            best = candidate
            break
    return best


def _row_id(cells, ac_column, default_prefix="AC"):
    """Pull the criterion id (AC- or SC-) out of a traceability/definition row."""
    if ac_column is not None and ac_column < len(cells):
        cell = cells[ac_column]
        found = ids_in(cell)
        if found:
            return found[0]
        if BARE_ID_RE.match(cell.strip()):
            return "%s-%s" % (default_prefix, cell.strip().upper())
    for cell in cells:
        found = ids_in(cell)
        if found:
            return found[0]
    return None


def _proof_column(table, ac_column):
    for index, cell in enumerate(table["header"]):
        if index == ac_column:
            continue
        lowered = re.sub(r"[*_`]", "", cell).strip().lower()
        if any(word in lowered for word in PROOF_HEADER_WORDS):
            return index
    return None


def _task_column(table, ac_column, proof_column):
    for index, cell in enumerate(table["header"]):
        if index in (ac_column, proof_column):
            continue
        lowered = re.sub(r"[*_`]", "", cell).strip().lower()
        if any(word in lowered for word in TASK_HEADER_WORDS):
            return index
    return None


def _traceability_columns(table):
    """Return ``(ac_col, proof_col, task_col)`` when the table is a traceability table."""
    column = _ac_column(table)
    if column is None:
        return None
    proof = _proof_column(table, column)
    task = _task_column(table, column, proof)
    if proof is None and task is None:
        return None
    return column, proof, task


def analyse(path, require_rows=False):
    """Return ``(result_dict, problems, warnings)`` for a Markdown document."""
    problems = []
    warnings = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit("error: cannot read file %s: %s" % (path, exc))
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()

    tables = _tables(lines)
    table_line_numbers = set()
    for table in tables:
        table_line_numbers.add(table["header_line"])
        for line_no, _cells in table["rows"]:
            table_line_numbers.add(line_no)
    sections = _criterion_sections(lines)

    def section_for(line_no):
        """Return the criterion-section heading containing a 1-based line, or None."""
        for start, end, heading in sections:
            if start <= line_no - 1 < end:
                return heading
        return None

    has_traceability_table = any(
        _traceability_columns(table) is not None for table in tables
    )
    strict = require_rows or has_traceability_table
    label_severity = "error" if strict else "warning"

    definitions = {}
    definition_order = []
    criterion_items_seen = 0

    def define(identifier, line_no, description):
        if identifier in definitions:
            problems.append(
                Problem(
                    "duplicate_ac",
                    "duplicate acceptance criterion %s (first defined on line %d); "
                    "each AC id must be defined exactly once" % (identifier, definitions[identifier]["line"]),
                    line_no,
                )
            )
            return
        definitions[identifier] = {"id": identifier, "line": line_no, "text": description}
        definition_order.append(identifier)

    # 1. Definitions: list items and tables inside an Acceptance Criteria section.
    for line_no, raw in enumerate(lines, 1):
        if line_no in table_line_numbers or section_for(line_no) is None:
            continue
        match = LIST_RE.match(raw)
        if not match:
            continue
        item = match.group(1).strip()
        checkbox = CHECKBOX_RE.match(item)
        if checkbox:
            item = checkbox.group(1).strip()
        criterion_items_seen += 1
        found = ids_in(item)
        if found:
            # The first id is the criterion; any other id in the sentence is a reference.
            define(found[0], line_no, item)
        else:
            problems.append(
                Problem(
                    "ac_without_id",
                    "criterion has no stable id (AC-<n> or SC-<n>): %r; label it, "
                    "e.g. **AC-1** or Spec Kit's **SC-001**" % item[:120],
                    line_no,
                    severity=label_severity,
                )
            )

    for table in tables:
        heading = section_for(table["header_line"])
        if heading is None:
            continue
        default_prefix = "SC" if "success" in heading else "AC"
        column = _ac_column(table)
        for line_no, cells in table["rows"]:
            if any(cell.strip() for cell in cells):
                criterion_items_seen += 1
            identifier = _row_id(cells, column, default_prefix)
            if identifier:
                define(identifier, line_no, " | ".join(cells))
            elif any(cell.strip() for cell in cells):
                problems.append(
                    Problem(
                        "ac_without_id",
                        "criterion table row has no stable id; add an AC-<n> or SC-<n> label "
                        "in the first column",
                        line_no,
                        severity=label_severity,
                    )
                )

    # 2. Fallback when no Acceptance Criteria section exists.
    if not definitions:
        for line_no, raw in enumerate(lines, 1):
            if line_no in table_line_numbers:
                continue
            match = LIST_RE.match(raw)
            if not match:
                continue
            found = ids_in(match.group(1))
            for identifier in found:
                define(identifier, line_no, match.group(1).strip())
        if definitions:
            warnings.append(
                "no Acceptance Criteria section found; using AC ids from list items as "
                "the criterion definitions"
            )

    # 3. Traceability tables.
    rows = []
    row_ids = {}
    traceability_tables = []
    for table in tables:
        columns = _traceability_columns(table)
        if columns is None:
            continue
        column, proof, task = columns
        traceability_tables.append(table)
        if proof is None:
            problems.append(
                Problem(
                    "missing_proof_column",
                    "traceability table has no Proof/Evidence column; add one (for example "
                    "| AC | Task | Proof |) so each row proves its criterion",
                    table["header_line"],
                )
            )
        for line_no, cells in table["rows"]:
            identifier = _row_id(cells, column)
            if identifier is None:
                problems.append(
                    Problem(
                        "row_without_id",
                        "traceability row has no AC id; start the row with AC-<n>",
                        line_no,
                    )
                )
                continue
            if identifier in row_ids:
                problems.append(
                    Problem(
                        "duplicate_row",
                        "duplicate traceability row for %s (first row on line %d)"
                        % (identifier, row_ids[identifier]),
                        line_no,
                    )
                )
                continue
            row_ids[identifier] = line_no
            row = {"id": identifier, "line": line_no, "cells": cells}
            if proof is not None:
                raw_proof = cells[proof] if proof < len(cells) else ""
                proof_text = raw_proof.strip()
                row["proof"] = proof_text
                if proof_text.lower() in PLACEHOLDERS:
                    # Person-checked criteria can be proven by an acceptance case/UAT column.
                    fallback = None
                    for index, cell in enumerate(table["header"]):
                        if index in (proof, column):
                            continue
                        lowered_header = re.sub(r"[*_`]", "", cell).strip().lower()
                        if not any(word in lowered_header for word in ACCEPTANCE_CASE_WORDS):
                            continue
                        if index < len(cells) and cells[index].strip().lower() not in PLACEHOLDERS:
                            fallback = cells[index].strip()
                            break
                    if fallback:
                        row["proof"] = fallback
                        row["proof_source"] = "acceptance_case"
                    else:
                        problems.append(
                            Problem(
                                "missing_proof",
                                "missing proof for %s in the traceability row; fill the "
                                "Proof/Evidence column (or an Acceptance case/UAT column) "
                                "with the command, test or artifact that proves the "
                                "criterion" % identifier,
                                line_no,
                            )
                        )
            else:
                row["proof"] = None
            if task is not None:
                row["task"] = cells[task].strip() if task < len(cells) else ""
            rows.append(row)

    # 4. Task references (outside AC sections and tables).
    tasks = []
    task_ids = set()
    for line_no, raw in enumerate(lines, 1):
        if line_no in table_line_numbers or section_for(line_no) is not None:
            continue
        match = LIST_RE.match(raw)
        if not match:
            continue
        item = match.group(1).strip()
        checkbox = CHECKBOX_RE.match(item)
        if checkbox:
            item = checkbox.group(1).strip()
        found = ids_in(item)
        if found:
            tasks.append({"line": line_no, "ids": found, "text": item[:200]})
            task_ids.update(found)

    # 5. Coverage. Rows with proof are mandatory when a traceability table is present (or
    # when --require-rows asks for strictness). A plain upstream spec.md that only lists
    # criteria is not reported as broken; the row requirement is a warning there.
    if not definitions and rows:
        for row in rows:
            if row["id"] not in definitions:
                definitions[row["id"]] = {
                    "id": row["id"],
                    "line": row["line"],
                    "text": "(implicit)",
                }
                definition_order.append(row["id"])
        warnings.append(
            "no explicit criterion definitions found; using ids referenced in the "
            "traceability table"
        )
    if not definitions:
        if criterion_items_seen:
            warnings.append(
                "criteria found but none carries a stable id; add AC-<n> / SC-<n> labels "
                "before relying on traceability"
            )
        else:
            problems.append(
                Problem(
                    "no_acceptance_criteria",
                    "no acceptance criteria found; add an 'Acceptance Criteria' section with "
                    "labelled items (AC-1, AC-2, ...) or Spec Kit's 'Success Criteria' "
                    "section with SC-001, SC-002, ...",
                )
            )
    coverage_severity = "error" if strict else "warning"
    missing = [identifier for identifier in definition_order if identifier not in row_ids]
    if traceability_tables:
        for identifier in missing:
            definition = definitions[identifier]
            if identifier in task_ids:
                message = (
                    "%s is referenced by a task but has no traceability row with proof; add "
                    "a row | %s | <task> | <proof> |" % (identifier, identifier)
                )
            else:
                message = (
                    "%s has no traceability row; add a row | %s | <task> | <proof> | to "
                    "the traceability table" % (identifier, identifier)
                )
            problems.append(Problem("missing_row", message, definition["line"]))
    elif tasks:
        for identifier in missing:
            problems.append(
                Problem(
                    "missing_coverage",
                    "%s is not referenced by any task and has no traceability row; add a "
                    "traceability table (| Criterion | Task | Proof |) or reference it from "
                    "a task" % identifier,
                    definitions[identifier]["line"],
                    severity=coverage_severity,
                )
            )
    elif definitions:
        problems.append(
            Problem(
                "no_traceability",
                "no traceability table or task references found; add a table with columns "
                "| Criterion | Task | Proof | after the criteria"
                + (
                    ""
                    if strict
                    else " (pass --require-rows to make this an error)"
                ),
                severity=coverage_severity,
            )
        )
    for row in rows:
        if definitions and row["id"] not in definitions:
            problems.append(
                Problem(
                    "orphan_row",
                    "%s appears in the traceability table but is not defined as an "
                    "acceptance criterion; define it under 'Acceptance Criteria' or fix the id"
                    % row["id"],
                    row["line"],
                )
            )

    problems.sort(key=lambda problem: (problem["line"] or 0, problem["code"]))
    error_problems = [problem for problem in problems if problem["severity"] == "error"]
    warning_problems = [problem for problem in problems if problem["severity"] == "warning"]
    result = {
        "file": str(Path(path)),
        "require_rows": require_rows,
        "ok": not error_problems,
        "summary": {
            "criteria": len(definition_order),
            "rows": len(rows),
            "tasks": len(tasks),
            "problems": len(error_problems),
            "warnings": len(warnings) + len(warning_problems),
        },
        "acceptance_criteria": [definitions[identifier] for identifier in definition_order],
        "rows": rows,
        "tasks": tasks,
        "problems": problems,
        "warnings": warnings,
    }
    return result, problems, warnings


def traceability(path, require_rows=False):
    """Analyse a document; returns ``(result, exit_code)``."""
    result, _problems, _warnings = analyse(path, require_rows=require_rows)
    return result, 0 if result["ok"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="traceability.py",
        description=(
            "Check that acceptance criteria (AC-<id>) and Spec Kit success criteria "
            "(SC-<id>) are defined once, have traceability rows and proof, and are covered "
            "by tasks. Read-only: it never edits the file."
        ),
        epilog=(
            "Rows with proof are required whenever a traceability table is present; for a "
            "plain spec.md without one, pass --require-rows to enforce them. "
            "Exit codes: 0 = traceable, 1 = problems found, 2 = bad usage. "
            "Example: traceability.py --file specs/001-feature/spec.md --require-rows --json"
        ),
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        required=True,
        help="Markdown spec/plan/tasks file to analyse",
    )
    parser.add_argument(
        "--require-rows",
        action="store_true",
        help="fail when a criterion has no traceability row with proof, even without a "
        "traceability table (strict mode for intaking-ticket artifacts)",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)

    path = Path(args.file).expanduser()
    if not path.is_file():
        print("error: file not found: %s" % args.file, file=sys.stderr)
        return 1
    result, problems, warnings = analyse(path, require_rows=args.require_rows)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("traceability: %s" % result["file"])
        identifiers = [item["id"] for item in result["acceptance_criteria"]]
        print(
            "criteria: %d%s"
            % (
                len(identifiers),
                " (%s)" % ", ".join(identifiers) if identifiers else "",
            )
        )
        print("traceability rows: %d" % len(result["rows"]))
        referenced = len([task for task in result["tasks"] if task["ids"]])
        print(
            "tasks: %d (%d reference criteria)"
            % (len(result["tasks"]), referenced)
        )
        for warning in warnings:
            print("warn: %s" % warning)
        for problem in problems:
            location = "%s:%s" % (path, problem["line"]) if problem["line"] else str(path)
            if problem["severity"] == "warning":
                print("warn %s: %s" % (location, problem["message"]))
            else:
                print("FAIL %s: %s" % (location, problem["message"]))
        if result["ok"]:
            print(
                "OK: %d criteria, %d traceability rows, no problems"
                % (len(identifiers), len(result["rows"]))
            )
            if any(problem["severity"] == "warning" for problem in problems):
                print(
                    "hint: pass --require-rows to make missing traceability rows an error"
                )
        else:
            print(
                "FAIL: %d problem(s) in %s"
                % (result["summary"]["problems"], result["file"])
            )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
