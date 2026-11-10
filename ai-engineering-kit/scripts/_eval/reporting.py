"""Per-trial aggregation. No majority vote, invented usage, or synthetic release proof."""
from __future__ import annotations

from collections import defaultdict

from .contracts import ContractError, digest, validate


def grade_dimensions(assertions: list[dict]) -> dict:
    result = {}
    for dimension in ("outcome", "compliance", "safety"):
        rows = [a for a in assertions if a["dimension"] == dimension and a.get("required", True)
                and a["status"] != "not-applicable"]
        states = {a["status"] for a in rows}
        result[dimension] = ("fail" if "fail" in states else
                             "unavailable" if not rows or "unavailable" in states else
                             "pending-review" if "pending-review" in states else "pass")
    critical = [a for a in assertions if a.get("critical") and a["status"] == "fail"
                and a["dimension"] in ("outcome", "safety")]
    result["critical_violations"] = len(critical)
    if critical:
        result["outcome"] = "fail"
    return result


def _ratio(top: int, bottom: int):
    return top / bottom if bottom else None


def _summary(rows: list[dict]) -> dict:
    started = [r for r in rows if r["status"] != "planned"]
    completed = [r for r in started if r["status"] == "completed"]
    dimensions = [(r, grade_dimensions(r["assertions"])) for r in completed]
    graded = [g for _, g in dimensions if g["outcome"] in ("pass", "fail")]
    passed = sum(g["outcome"] == "pass" for g in graded)
    token_values = [(r.get("usage") or {}).get("total_tokens") for r in started]
    known = [n for n in token_values if type(n) is int and n >= 0]
    compliance = [g["compliance"] for _, g in dimensions if g["compliance"] in ("pass", "fail")]
    return {"scheduled": len(rows), "started": len(started), "completed": len(completed),
            "graded": len(graded), "successes": passed,
            "pending_review": sum(g["outcome"] == "pending-review" for _, g in dimensions),
            "unavailable": sum(g["outcome"] == "unavailable" for _, g in dimensions),
            "errors": sum(r["status"] not in ("completed", "planned") for r in rows),
            "quality_rate": _ratio(passed, len(graded)),
            "end_to_end_rate": _ratio(passed, len(started)),
            "coverage": _ratio(len(graded), len(started)),
            "all_trials_success": (False if any(g["outcome"] == "fail" for g in graded)
                                   or any(r["status"] not in ("completed", "planned") for r in rows)
                                   else True if rows and len(graded) == len(rows) and passed == len(rows) else None),
            "compliance_rate": _ratio(compliance.count("pass"), len(compliance)),
            "critical_violations": sum(g["critical_violations"] for _, g in dimensions),
            "duration_s": round(sum(r["duration_s"] for r in started), 6),
            "total_tokens": sum(known) if started and len(known) == len(started) else None,
            "known_tokens": sum(known), "usage_coverage": _ratio(len(known), len(started)),
            "cost_usd": None, "cost_per_success_usd": None,
            "human_interventions": None}


def aggregate(trials: list[dict], *, manifest: dict | None = None) -> dict:
    if len({r["synthetic"] for r in trials}) > 1:
        raise ContractError("cannot mix synthetic and real trials")
    if len({r["id"] for r in trials}) != len(trials):
        raise ContractError("duplicate trial IDs")
    groups: dict[str, list] = defaultdict(list)
    scenarios: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for row in trials:
        groups[row["variant"]].append(row)
        scenarios[row["scenario"]][row["variant"]].append(row)
    per_scenario = []
    for name, variants in sorted(scenarios.items()):
        summaries = {key: _summary(value) for key, value in sorted(variants.items())}
        baseline = summaries.get("no-kit", {}).get("quality_rate")
        candidate = summaries.get("full-kit", {}).get("quality_rate")
        per_scenario.append({"id": name, "variants": summaries,
                             "delta": candidate - baseline if candidate is not None and baseline is not None else None})
    report = {"schema": "aiek-eval-report/2", "synthetic": bool(trials and trials[0]["synthetic"]),
            "manifest_hash": digest(manifest) if manifest else None,
            "variants": {key: _summary(value) for key, value in sorted(groups.items())},
            "per_scenario": per_scenario, "trial_ids": [r["id"] for r in trials],
            "verdict": "inconclusive", "release_proof": False,
            "limitations": ["Small pilot; no statistical superiority claim.",
                            "Cost unavailable without a versioned price table and complete usage.",
                            "Unknown observations are not failures or proof of absence."]}
    validate("report", report)
    return report


def markdown_report(report: dict) -> str:
    def pct(value):
        return "unavailable" if value is None else f"{value:.1%}"
    lines = ["# Eval report", "", f"Synthetic: {report['synthetic']}. Verdict: {report['verdict']}.", "",
             "Quality = successes / graded completed trials; end-to-end = successes / all started trials.",
             "Coverage = graded completed / all started. Errors stay in end-to-end denominator.", "",
             "| Variant | Success/graded | Quality | End-to-end | Coverage | Errors | Critical | Tokens |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, s in report["variants"].items():
        lines.append(f"| {name} | {s['successes']}/{s['graded']} | {pct(s['quality_rate'])} | "
                     f"{pct(s['end_to_end_rate'])} | {pct(s['coverage'])} | {s['errors']} | "
                     f"{s['critical_violations']} | {s['total_tokens']} |")
    lines.extend(["", "## Per scenario", ""])
    for row in report["per_scenario"]:
        lines.append(f"- {row['id']}: outcome delta {row['delta']} (full-kit minus no-kit).")
    lines.extend(["", "## Limits", "", *[f"- {s}" for s in report["limitations"]], ""])
    return "\n".join(lines)
