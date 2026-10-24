#!/usr/bin/env python3
"""Trigger evaluation for the AI Engineering Kit.

Runs the 25-query trigger set in ``evals/trigger.json`` against an agent harness and
reports precision, recall, accuracy and a wrong-skill matrix. The eval is
harness-agnostic:

    --harness dsh      DeepSeek Harness   (dsh headless --json; primary)
    --harness claude   Claude Code        (claude -p --output-format json)
    --harness codex    Codex CLI          (codex exec --json)
    --harness mock     deterministic offline keyword scorer (no network, CI-safe)
    --harness auto     probe dsh > claude > codex and use the first that works (default)

Real harnesses run inside a throw-away scratch project with the kit installed (the
same ``scripts/install.sh`` a user runs), so skill discovery is tested for real.
dsh skill usage is read from actual ``skill`` tool-call events, not from the
self-reported line; claude/codex fall back to the declared ``SKILL_USED:`` line and
are marked with ``"source": "declared"`` in the JSON report.

Usage:
    python3 scripts/eval_trigger.py --mock                 # offline, fast (CI)
    python3 scripts/eval_trigger.py --harness auto --runs 3
    python3 scripts/eval_trigger.py --harness dsh --runs 1 --limit 5
    python3 scripts/eval_trigger.py --kit-root /tmp/aiek-baseline/ai-engineering-kit \\
        --kit-label baseline-main-85f27c7 --mock

Exit codes: 0 = accuracy >= threshold, 1 = eval ran but below threshold,
2 = configuration/harness error (nothing scored). Never fabricates a score: a
harness failure is recorded as an error and never counted as a pass.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "aiek-trigger-eval/1"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_KIT_ROOT = SCRIPT_DIR.parent
DEFAULT_THRESHOLD = 0.90
DEFAULT_RUNS = 3
DEFAULT_TIMEOUT = 300
DEFAULT_PROBE_TIMEOUT = 120

# Suffix appended to every query. It asks for a machine-readable declaration and
# keeps answers short (cost/time control); it does not tell the agent what to choose.
PROMPT_SUFFIX = (
    "\n\nNow answer as a trigger-eval probe. Do not implement or edit any files. "
    "On the first line write `SKILL_USED: <the skill names you actually opened, "
    "comma-separated; or none>`. Then answer in at most 2 sentences."
)

# Harness -> install.sh --harness value (which skills root the tool reads).
INSTALL_HARNESS = {"dsh": "codex", "claude": "claude", "codex": "codex"}

STOPWORDS = set(
    """a an and are as at be been before but by can could did do does doing done for from
    had has have how i if in into is it its just me more most my no nor not of on once
    only or other our out over own same she should so some such than that the their them
    then there these they this those through to too under until up use used uses using
    very was we were what when where which while who whom why will with would you your
    yours yourself skill skills request requests task tasks work working change changes
    new existing current already also may might must shall via per non etc e g i.e
    project projects code coding thing things something request know understand wondering""".split()
)

SKILL_NAME_RE = re.compile(r"[a-z][a-z0-9-]*")
DECLARED_RE = re.compile(r"(?im)^\s*[-*`> ]*SKILL_USED\s*:\s*(?P<names>.*?)\s*$")
NONE_WORDS = {"none", "no", "nothing", "null", "-", "n/a", "na", "no skill", "no skills"}


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def which(name: str) -> str | None:
    return shutil.which(name)


def run_process(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: float,
    env: dict[str, str] | None = None,
) -> tuple[int | None, str, str, float, list[str]]:
    """Run a subprocess with a hard timeout. Returns (rc, stdout, stderr, seconds, cmd).

    rc is None on timeout/OSError. The timeout is enforced with subprocess.run; macOS
    has no timeout(1) binary, so the Python-level timeout is the portable mechanism.
    """
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or "", time.monotonic() - started, cmd
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
        return None, out or "", (err or "") + f"\n[eval] timeout after {timeout:.0f}s", time.monotonic() - started, cmd
    except OSError as exc:
        return None, "", f"[eval] cannot execute {cmd[0]}: {exc}", time.monotonic() - started, cmd


# --------------------------------------------------------------------------- #
# Skill metadata
# --------------------------------------------------------------------------- #

def parse_frontmatter_description(text: str) -> str:
    """Extract ``description`` from a SKILL.md frontmatter without requiring PyYAML."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return ""
    front = match.group(1)
    lines = front.splitlines()
    desc_lines: list[str] = []
    collecting = False
    block_indent: int | None = None
    for line in lines:
        if not collecting:
            m = re.match(r"^description\s*:\s*(.*)$", line)
            if not m:
                continue
            value = m.group(1).strip()
            if value in ("|", ">", "|-", ">-"):
                collecting = True
                block_indent = None
                continue
            return _unquote(value)
        # block scalar: collect indented lines
        if not line.strip():
            desc_lines.append("")
            continue
        indent = len(line) - len(line.lstrip())
        if block_indent is None:
            block_indent = indent
        if indent < block_indent:
            break
        desc_lines.append(line[block_indent:])
    if desc_lines:
        joined = "\n".join(desc_lines).strip()
        return re.sub(r"\s+", " ", joined)
    return ""


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n")
        return re.sub(r"\s+", " ", inner).strip()
    return value


def load_skill_descriptions(kit_root: Path) -> dict[str, str]:
    skills_dir = kit_root / "skills"
    if not skills_dir.is_dir():
        raise SystemExit(f"error: skills directory not found under kit root: {skills_dir}")
    descriptions: dict[str, str] = {}
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        descriptions[skill_dir.name] = parse_frontmatter_description(skill_file.read_text(encoding="utf-8"))
    if not descriptions:
        raise SystemExit(f"error: no skills found under {skills_dir}")
    return descriptions


def load_queries(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    queries = data.get("queries")
    if not isinstance(queries, list) or not queries:
        raise SystemExit(f"error: no queries in {path}")
    seen: set[str] = set()
    for query in queries:
        for key in ("id", "prompt", "expected_skills"):
            if key not in query:
                raise SystemExit(f"error: query missing {key!r}: {query}")
        if query["id"] in seen:
            raise SystemExit(f"error: duplicate query id {query['id']}")
        seen.add(query["id"])
        if not isinstance(query["expected_skills"], list):
            raise SystemExit(f"error: expected_skills must be a list in {query['id']}")
        query.setdefault("kind", "should-trigger" if query["expected_skills"] else "near-miss")
        query.setdefault("preferred_skills", list(query["expected_skills"]))
        query.setdefault("reason", "")
    return queries


def normalize_skill_names(raw: str) -> list[str]:
    """Parse a SKILL_USED value into canonical skill names (case/whitespace tolerant)."""
    cleaned = raw.strip().strip("`\"'")
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)  # drop parenthetical commentary
    found: list[str] = []
    if cleaned.lower() in NONE_WORDS:
        return []
    for token in re.split(r"[,;/|]+|\band\b|\s{2,}", cleaned):
        token = token.strip().strip("`\"'.").lower()
        token = token.replace("_", "-").replace(" ", "-")
        token = re.sub(r"^(skill|skills)[:-]", "", token)
        # Installed skills carry the installer's namespace (default `aiek-`); the evals
        # compare against bare kit names, so strip it before matching.
        token = re.sub(r"^aiek-", "", token)
        if not token or token in NONE_WORDS:
            continue
        if SKILL_NAME_RE.fullmatch(token):
            found.append(token)
    # A single unseparated sentence like "executing-task (small fix)" leaves garbage; keep known-ish tokens.
    if not found and cleaned and cleaned.lower() not in NONE_WORDS:
        for token in re.findall(r"[a-z][a-z0-9-]+", cleaned.lower()):
            if token in NONE_WORDS:
                continue
            found.append(token)
    deduped: list[str] = []
    for name in found:
        if name not in deduped:
            deduped.append(name)
    return deduped


def parse_declared_skills(text: str) -> list[str]:
    match = DECLARED_RE.search(text or "")
    if not match:
        return []
    return normalize_skill_names(match.group("names"))


# --------------------------------------------------------------------------- #
# Harness adapters
# --------------------------------------------------------------------------- #

@dataclass
class HarnessResult:
    skills_used: list[str] = field(default_factory=list)
    source: str = "none"          # tool_call | declared | heuristic | none
    text: str = ""
    duration_s: float = 0.0
    usage: dict = field(default_factory=dict)
    error: str | None = None
    command: list[str] = field(default_factory=list)
    raw_excerpt: str = ""


class HarnessError(RuntimeError):
    """A harness could not run (missing binary, auth failure, timeout, crash)."""


class Harness:
    name = "base"

    def probe(self, cwd: Path, env: dict[str, str] | None, timeout: float) -> dict:
        raise NotImplementedError

    def run(self, prompt: str, cwd: Path, env: dict[str, str] | None, timeout: float) -> HarnessResult:
        raise NotImplementedError


class DshHarness(Harness):
    """DeepSeek Harness: skill use is read from real tool_call events (ground truth)."""

    name = "dsh"

    def __init__(self) -> None:
        self.binary = which("dsh")
        if not self.binary:
            raise HarnessError("dsh not found on PATH (expected ~/.local/bin/dsh)")

    def command(self, prompt: str) -> list[str]:
        return [self.binary, "headless", "--json", prompt]

    def parse(self, stdout: str, stderr: str, duration_s: float, timeout: float) -> HarnessResult:
        skills: list[str] = []
        texts: list[str] = []
        errors: list[str] = []
        usage_steps: list[dict] = []
        raw_lines = 0
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            raw_lines += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            etype = event.get("type")
            if etype == "tool_call" and event.get("tool") == "skill":
                payload = event.get("input") or {}
                name = payload.get("name") or payload.get("skill")
                if isinstance(name, str):
                    skills.extend(normalize_skill_names(name))
            elif etype == "text" and isinstance(event.get("text"), str):
                texts.append(event["text"])
            elif etype == "error":
                errors.append(str(event.get("message") or event.get("error") or event)[:300])
            elif etype == "status" and event.get("usage"):
                usage_steps.append(event["usage"])
        combined = "\n".join(texts)
        declared = parse_declared_skills(combined)
        source = "tool_call"
        resolved = _dedupe(skills)
        if not resolved and declared:
            resolved = declared
            source = "declared"
        elif not resolved:
            source = "none"
        usage = _sum_usage(usage_steps)
        error = None
        if raw_lines == 0:
            error = "harness produced no JSON events"
        elif errors and not combined:
            error = "harness error: " + "; ".join(errors[:2])
        return HarnessResult(
            skills_used=resolved,
            source=source,
            text=combined,
            duration_s=duration_s,
            usage=usage,
            error=error,
            raw_excerpt=(stdout or stderr)[-1200:],
            command=[],
        )

    def run(self, prompt: str, cwd: Path, env: dict[str, str] | None, timeout: float) -> HarnessResult:
        cmd = self.command(prompt)
        rc, out, err, duration, _ = run_process(cmd, cwd=cwd, timeout=timeout, env=env)
        result = self.parse(out, err, duration, timeout)
        result.command = [Path(cmd[0]).name, *cmd[1:-1], "<prompt>"]
        if rc is None:
            result.error = (err.strip() or "timeout")[-800:]
            result.text = result.text or out[-1200:]
        elif rc != 0 and not result.text:
            result.error = f"harness exited {rc}: {(err or out).strip()[-800:]}"
        return result

    def probe(self, cwd: Path, env: dict[str, str] | None, timeout: float) -> dict:
        result = self.run("Reply with exactly: PROBE_OK", cwd, env, timeout)
        ok = False if result.error else bool(re.search(r"PROBE_OK", result.text))
        return {
            "harness": "dsh",
            "ok": ok,
            "source": result.source,
            "detail": "probe returned PROBE_OK" if ok else (result.error or "no PROBE_OK in output")[-500:],
        }


class ClaudeHarness(Harness):
    """Claude Code. Skill tool events are not reliably exported by -p, so the
    declared SKILL_USED line is used (marked as source=declared)."""

    name = "claude"

    def __init__(self) -> None:
        self.binary = which("claude")
        if not self.binary:
            raise HarnessError("claude not found on PATH")

    def command(self, prompt: str) -> list[str]:
        return [self.binary, "-p", prompt, "--output-format", "json"]

    def run(self, prompt: str, cwd: Path, env: dict[str, str] | None, timeout: float) -> HarnessResult:
        cmd = self.command(prompt)
        rc, out, err, duration, _ = run_process(cmd, cwd=cwd, timeout=timeout, env=env)
        result = HarnessResult(duration_s=duration, command=[Path(cmd[0]).name, "-p", "<prompt>", "--output-format", "json"])
        text = ""
        try:
            data = json.loads(out)
        except (json.JSONDecodeError, TypeError):
            data = None
        if isinstance(data, dict):
            if data.get("is_error"):
                result.error = f"claude error: {str(data.get('result') or data.get('error') or 'unknown')[:600]}"
            text = str(data.get("result") or "")
            usage = data.get("usage") or {}
            if isinstance(usage, dict):
                result.usage = {
                    "totalTokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
                    "outputTokens": usage.get("output_tokens") or 0,
                }
            messages = data.get("messages")
            tool_skills: list[str] = []
            if isinstance(messages, list):
                for message in messages:
                    for block in (message or {}).get("content") or []:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name") or ""
                            if str(name).lower() in ("skill", "skills"):
                                payload = block.get("input") or {}
                                raw = payload.get("skill") or payload.get("name")
                                if isinstance(raw, str):
                                    tool_skills.extend(normalize_skill_names(raw))
            declared = parse_declared_skills(text)
            if tool_skills:
                result.skills_used, result.source = _dedupe(tool_skills), "tool_call"
            elif declared:
                result.skills_used, result.source = declared, "declared"
        else:
            text = out
        result.text = text
        if rc is None:
            result.error = (err.strip() or "timeout")[-800:]
        elif rc != 0 and not result.text:
            result.error = f"claude exited {rc}: {(err or out).strip()[-800:]}"
        return result

    def probe(self, cwd: Path, env: dict[str, str] | None, timeout: float) -> dict:
        result = self.run("Reply with exactly: PROBE_OK", cwd, env, timeout)
        ok = False if result.error else bool(re.search(r"PROBE_OK", result.text))
        return {
            "harness": "claude",
            "ok": ok,
            "detail": "probe returned PROBE_OK" if ok else (result.error or "no PROBE_OK in output")[-500:],
        }


class CodexHarness(Harness):
    """Codex CLI. The skill tool call is not exposed in the JSON stream, so the
    declared SKILL_USED line is used (marked source=declared)."""

    name = "codex"

    def __init__(self) -> None:
        self.binary = which("codex")
        if not self.binary:
            raise HarnessError("codex not found on PATH")

    def command(self, prompt: str) -> list[str]:
        return [self.binary, "exec", "--json", "--skip-git-repo-check", prompt]

    def run(self, prompt: str, cwd: Path, env: dict[str, str] | None, timeout: float) -> HarnessResult:
        cmd = self.command(prompt)
        rc, out, err, duration, _ = run_process(cmd, cwd=cwd, timeout=timeout, env=env)
        texts: list[str] = []
        usage: dict = {}
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            etype = event.get("type")
            if etype == "item.completed":
                item = event.get("item") or {}
                if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                    texts.append(item["text"])
            elif etype == "turn.completed" and isinstance(event.get("usage"), dict):
                raw = event["usage"]
                usage = {
                    "totalTokens": (raw.get("input_tokens") or 0) + (raw.get("output_tokens") or 0),
                    "outputTokens": raw.get("output_tokens") or 0,
                }
        combined = "\n".join(texts)
        declared = parse_declared_skills(combined)
        result = HarnessResult(
            skills_used=declared,
            source="declared" if declared else "none",
            text=combined,
            duration_s=duration,
            usage=usage,
            command=[Path(cmd[0]).name, "exec", "--json", "--skip-git-repo-check", "<prompt>"],
            raw_excerpt=(out or err)[-1200:],
        )
        if rc is None:
            result.error = (err.strip() or "timeout")[-800:]
        elif rc != 0 and not combined:
            result.error = f"codex exited {rc}: {(err or out).strip()[-800:]}"
        return result

    def probe(self, cwd: Path, env: dict[str, str] | None, timeout: float) -> dict:
        result = self.run("Reply with exactly: PROBE_OK", cwd, env, timeout)
        ok = False if result.error else bool(re.search(r"PROBE_OK", result.text))
        return {
            "harness": "codex",
            "ok": ok,
            "detail": "probe returned PROBE_OK" if ok else (result.error or "no PROBE_OK in output")[-500:],
        }


# --------------------------------------------------------------------------- #
# Mock harness: deterministic keyword scorer (offline / CI)
# --------------------------------------------------------------------------- #

def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.findall(r"[a-z0-9][a-z0-9'-]*", (text or "").lower()):
        token = raw.strip("'-")
        if token:
            tokens.append(token)
    return tokens


IRREGULAR_STEMS = {
    "built": "build", "made": "make", "wrote": "writ", "written": "writ", "ran": "run",
    "found": "find", "left": "leav", "did": "do", "done": "do", "went": "go", "gone": "go",
    "kept": "keep", "saw": "see", "seen": "see", "bought": "buy", "gave": "give",
    "given": "give", "took": "take", "taken": "take", "came": "come", "became": "becom",
}


def stem(token: str) -> str:
    """Tiny deterministic stemmer (plural/gerund/past). Both sides of a match use it,
    so a consistent truncation is enough; it is not a full Porter stemmer."""
    token = token.strip("'-")
    if token in IRREGULAR_STEMS:
        return IRREGULAR_STEMS[token]
    for suffix in ("ing", "edly", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            token = token[: -len(suffix)]
            break
    if len(token) > 4 and token.endswith("e"):
        token = token[:-1]
    return token


NEGATIVE_MARKER_RE = re.compile(
    r"\b(not\s+for|not\s+used\s+for|do\s+not\s+use|don't\s+use|excludes?|excluded?|"
    r"not\s+a\s+substitute|instead\s+use)\b",
    re.I,
)
TRIGGER_MARKER_RE = re.compile(
    r"\b(use\s+when|use\s+this\s+when|trigger\s+when|triggers?|invoke\s+when|"
    r"call\s+this\s+when|start\s+with)\b",
    re.I,
)


class MockHarness(Harness):
    """Deterministic offline scorer used by CI and by baseline snapshots.

    This is a keyword heuristic over the *installed skill descriptions*, not a model:
    it measures whether descriptions carry trigger vocabulary (``Use when ...``) and
    negative vocabulary (``Not for ...``). It is intentionally labeled as a proxy in
    every report; real triggering evidence must come from a real harness.
    """

    name = "mock"

    def __init__(self, descriptions: dict[str, str]) -> None:
        self.descriptions = descriptions
        self.analysis = {name: self._analyze(desc) for name, desc in descriptions.items()}
        document_frequency: dict[str, int] = {}
        for parsed in self.analysis.values():
            for token in parsed["content_tokens"]:
                document_frequency[token] = document_frequency.get(token, 0) + 1
        skill_count = max(1, len(self.analysis))
        # Terms present in >= 40% of the descriptions carry no discrimination signal.
        generic_cutoff = max(3, math.ceil(skill_count * 0.4))
        self.generic = {token for token, df in document_frequency.items() if df >= generic_cutoff}
        for token in STOPWORDS:
            self.generic.add(stem(token))
        self.document_frequency = document_frequency
        self.idf = {
            token: round(math.log(1 + len(self.analysis) / (1 + df)), 3)
            for token, df in document_frequency.items()
        }

    @staticmethod
    def _analyze(description: str) -> dict:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", description or "")
        trigger_parts: list[str] = []
        negative_parts: list[str] = []
        for sentence in sentences:
            if not sentence.strip():
                continue
            if NEGATIVE_MARKER_RE.search(sentence):
                negative_parts.append(sentence)
            elif TRIGGER_MARKER_RE.search(sentence):
                # "rather than a failing test" points at a comparison skill; drop that
                # clause but keep the trigger examples that follow it.
                trigger_parts.append(re.sub(r"\s+rather\s+than\s+[^,;.\-\u2013\u2014]+", " ", sentence, flags=re.I))
        # No explicit trigger sentence: the whole description is weak trigger vocabulary.
        weak_trigger = not trigger_parts
        if weak_trigger:
            trigger_parts = [description or ""]
        trigger_text = " ".join(trigger_parts)
        negative_text = " ".join(negative_parts)
        trigger_tokens = {stem(token) for token in tokenize(trigger_text)} - STOPWORDS
        negative_tokens = {stem(token) for token in tokenize(negative_text)} - STOPWORDS
        full_tokens = {stem(token) for token in tokenize(description or "")} - STOPWORDS
        # Negative vocabulary only matters when it is NOT also positive vocabulary.
        exclusive_negative = negative_tokens - trigger_tokens
        example_token_sets: list[set[str]] = []
        coverage_phrases: list[str] = list(
            re.findall(r"[\'\"\u201c\u201d]([^\'\"\u201c\u201d]{3,160})[\'\"\u201c\u201d]", trigger_text)
        )
        # Comma/dash separated trigger phrases ("failing tests with no obvious reason,
        # a flaky test, ...") are examples too, even without quotation marks.
        coverage_phrases.extend(part for part in re.split(r"[,;]|\s+-\s+", trigger_text) if part and part.strip())
        for phrase in coverage_phrases:
            tokens = {stem(token) for token in tokenize(phrase)} - STOPWORDS
            if len(tokens) >= 1:
                example_token_sets.append(tokens)
        return {
            "trigger_tokens": trigger_tokens,
            "trigger_text": trigger_text,
            "negative_tokens": exclusive_negative,
            "content_tokens": full_tokens,
            "weak_trigger": weak_trigger,
            "example_token_sets": example_token_sets,
            "has_use_when": bool(re.search(r"use when", description or "", re.I)),
            "has_negative": bool(negative_parts),
        }

    def score_query(self, query: str) -> dict:
        raw_tokens = tokenize(query)
        content_all = [stem(token) for token in raw_tokens if token not in STOPWORDS]
        content = [token for token in content_all if token not in self.generic]
        bigrams = {(content[i], content[i + 1]) for i in range(len(content) - 1)}
        scores: dict[str, float] = {}
        disqualified: dict[str, str] = {}
        for name, parsed in self.analysis.items():
            negative_hits = sorted(set(content) & parsed["negative_tokens"])
            if negative_hits:
                disqualified[name] = "negative trigger: " + ", ".join(negative_hits)
                continue
            trigger_hits = sorted(set(content) & parsed["trigger_tokens"])
            word_score = sum(self.idf.get(token, 1.0) for token in trigger_hits)
            if parsed["weak_trigger"]:
                word_score *= 0.5
            bigram_score = sum(
                min(self.idf.get(bigram[0], 1.0), self.idf.get(bigram[1], 1.0))
                for bigram in bigrams
                if bigram[0] in parsed["trigger_tokens"] and bigram[1] in parsed["trigger_tokens"]
            )
            base_score = word_score + bigram_score
            coverage_bonus = 0.0
            if content_all:
                content_set = set(content_all)
                for example in parsed["example_token_sets"]:
                    coverage = len(example & content_set) / len(content_set)
                    if coverage >= 0.999:
                        coverage_bonus = max(coverage_bonus, 2.0)
                    elif coverage >= 0.5 and base_score > 0:
                        coverage_bonus = max(coverage_bonus, round(1.5 * coverage, 3))
            scores[name] = round(base_score + coverage_bonus, 3)
        best_score = max(scores.values()) if scores else 0.0
        if best_score <= 0.0:
            return {"skills_used": [], "source": "heuristic", "scores": scores, "disqualified": disqualified}
        winners = sorted(name for name, score in scores.items() if score == best_score)
        # Deterministic tie-break: lexicographic. A model would use semantics; the mock
        # reports this as heuristic selection only.
        return {
            "skills_used": [winners[0]],
            "source": "heuristic",
            "scores": {name: scores[name] for name in sorted(scores, key=lambda n: -scores[n]) if scores[name] > 0},
            "disqualified": disqualified,
        }

    def run(self, prompt: str, cwd: Path, env: dict[str, str] | None, timeout: float) -> HarnessResult:
        started = time.monotonic()
        if PROMPT_SUFFIX in prompt:
            prompt = prompt[: -len(PROMPT_SUFFIX)]
        scored = self.score_query(prompt)
        return HarnessResult(
            skills_used=scored["skills_used"],
            source="heuristic",
            text="",
            duration_s=time.monotonic() - started,
            usage={"totalTokens": 0, "outputTokens": 0},
            error=None,
            command=["mock-keyword-scorer"],
            raw_excerpt=json.dumps({k: scored[k] for k in ("scores", "disqualified")}, ensure_ascii=False)[:1200],
        )

    def probe(self, cwd: Path, env: dict[str, str] | None, timeout: float) -> dict:
        return {"harness": "mock", "ok": True, "detail": "deterministic keyword scorer (offline)"}


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _sum_usage(steps: list[dict]) -> dict:
    if not steps:
        return {}
    total = 0
    output = 0
    for step in steps:
        total += step.get("totalTokens") or 0
        output += step.get("outputTokens") or 0
    return {"totalTokens": total, "outputTokens": output, "steps": len(steps)}


# --------------------------------------------------------------------------- #
# Scratch project + harness selection
# --------------------------------------------------------------------------- #

def prepare_scratch(kit_root: Path, keep: bool) -> tuple[Path, dict, dict]:
    scratch = Path(tempfile.mkdtemp(prefix="aiek-trigger-"))
    env = dict(os.environ)
    # Isolate dsh from the user's global ~/.agents skills so only the installed kit is
    # discoverable. This is what makes a trigger measurement valid.
    empty_agents = scratch / ".isolated-agents-home"
    empty_agents.mkdir()
    env["DSH_AGENTS_HOME"] = str(empty_agents)
    (scratch / "README.md").write_text("scratch project for AI Engineering Kit trigger eval\n", encoding="utf-8")
    run_process([which("git") or "git", "init", "-q"], cwd=scratch, timeout=30)
    # Install both skill roots (.claude/skills and .agents/skills) so the probe can
    # resolve to whichever harness is installed, without a second install pass.
    install_cmd = ["bash", str(kit_root / "scripts" / "install.sh"), str(scratch)]
    rc, out, err, duration, _ = run_process(install_cmd, cwd=kit_root, timeout=180, env=dict(os.environ))
    install_info = {
        "command": [str(kit_root / "scripts" / "install.sh"), "<scratch>"],
        "returncode": rc,
        "duration_s": round(duration, 2),
        "ok": rc == 0,
        "stdout_excerpt": (out or "")[-800:],
        "stderr_excerpt": (err or "")[-800:],
    }
    if rc != 0:
        if not keep:
            shutil.rmtree(scratch, ignore_errors=True)
        raise HarnessError(f"install.sh failed ({rc}) into the scratch project: {(err or out)[-500:]}")
    return scratch, env, install_info


def description_coverage(kit_root: Path) -> dict:
    descriptions = load_skill_descriptions(kit_root)
    triggers = 0
    negatives = 0
    mock = MockHarness(descriptions)
    for parsed in mock.analysis.values():
        triggers += 1 if parsed["has_use_when"] else 0
        negatives += 1 if parsed["has_negative"] else 0
    return {"skills": len(descriptions), "with_use_when": triggers, "with_negative_trigger": negatives}


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def majority_skills(runs: list[HarnessResult]) -> tuple[list[str], list[dict]]:
    """Majority vote over N runs. A skill is observed if it appears in a strict
    majority of successful runs. If every run failed, the aggregated result is empty
    and carries the first error."""
    successful = [run for run in runs if run.error is None]
    if not successful:
        return [], [{"skills_used": run.skills_used, "source": run.source, "error": run.error} for run in runs]
    threshold = len(successful) / 2.0
    counts: dict[str, int] = {}
    for run in successful:
        for skill in run.skills_used:
            counts[skill] = counts.get(skill, 0) + 1
    observed = sorted(skill for skill, count in counts.items() if count > threshold)
    return observed, [
        {"skills_used": run.skills_used, "source": run.source, "error": run.error, "duration_s": round(run.duration_s, 2)}
        for run in runs
    ]


def evaluate(queries: list[dict], harness: Harness, *, runs: int, timeout: float,
             scratch: Path, env: dict | None, verbose: bool) -> dict:
    query_reports: list[dict] = []
    durations: list[float] = []
    total_tokens = 0
    for index, query in enumerate(queries, 1):
        run_results: list[HarnessResult] = []
        for attempt in range(runs):
            result = harness.run(query["prompt"] + PROMPT_SUFFIX, scratch, env, timeout)
            run_results.append(result)
            durations.append(result.duration_s)
            total_tokens += int((result.usage or {}).get("totalTokens") or 0)
            if verbose:
                eprint(
                    f"  [{index:02d}/{len(queries)}] {query['id']} run {attempt + 1}/{runs}: "
                    f"{result.skills_used or '-'} ({result.source}, {result.duration_s:.1f}s)"
                    + (f" ERROR {result.error[:160]}" if result.error else "")
                )
        observed, run_summaries = majority_skills(run_results)
        expected = [name for name in query["expected_skills"]]
        if expected:
            passed = any(skill in expected for skill in observed)
        else:
            passed = len(observed) == 0
        errors = [run.error for run in run_results if run.error]
        query_reports.append(
            {
                "id": query["id"],
                "kind": query.get("kind"),
                "skill_family": query.get("skill_family"),
                "prompt": query["prompt"],
                "expected_skills": expected,
                "preferred_skills": query.get("preferred_skills", expected),
                "observed_skills": observed,
                "passed": passed,
                "reason": query.get("reason", ""),
                "runs": run_summaries,
                "error": errors[0] if errors else None,
                "all_runs_failed": len(errors) == len(run_results),
            }
        )
    # Metrics: positive class = "a skill was expected"; acceptable = intersects expected.
    tp = fp = tn = fn = 0
    should_trigger_total = should_trigger_passed = 0
    near_miss_total = near_miss_passed = 0
    negative_total = negative_passed = 0
    for report in query_reports:
        expected = report["expected_skills"]
        observed = report["observed_skills"]
        if expected:
            if any(skill in expected for skill in observed):
                tp += 1
            else:
                fn += 1
            if report["kind"] == "should-trigger":
                should_trigger_total += 1
                should_trigger_passed += 1 if report["passed"] else 0
            else:
                near_miss_total += 1
                near_miss_passed += 1 if report["passed"] else 0
        else:
            if observed:
                fp += 1
            else:
                tn += 1
            near_miss_total += 1
            negative_total += 1
            near_miss_passed += 1 if report["passed"] else 0
            negative_passed += 1 if report["passed"] else 0
    total = len(query_reports)
    passed = sum(1 for report in query_reports if report["passed"])
    accuracy = passed / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    wrong_skill_matrix = []
    for report in query_reports:
        if report["passed"]:
            continue
        observed = report["observed_skills"]
        if not observed:
            category = "missed (no skill)" if report["expected_skills"] else "ok"
        elif not report["expected_skills"]:
            category = "false positive (skill used on negative)"
        else:
            category = "wrong skill"
        wrong_skill_matrix.append(
            {
                "id": report["id"],
                "prompt": report["prompt"],
                "category": category,
                "expected": report["expected_skills"],
                "observed": observed,
                "preferred": report["preferred_skills"],
            }
        )
    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "should_trigger": {"total": should_trigger_total, "passed": should_trigger_passed},
            "near_miss": {"total": near_miss_total, "passed": near_miss_passed},
            "negative": {"total": negative_total, "passed": negative_passed},
            "avg_duration_s": round(sum(durations) / len(durations), 2) if durations else 0.0,
            "total_tokens": total_tokens,
        },
        "queries": query_reports,
        "wrong_skill_matrix": wrong_skill_matrix,
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trigger eval for the AI Engineering Kit (25 queries; 15 should-trigger + 10 near-miss).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  python3 scripts/eval_trigger.py --mock\n"
        "  python3 scripts/eval_trigger.py --harness dsh --runs 3\n"
        "  python3 scripts/eval_trigger.py --harness auto --limit 10 --json\n",
    )
    parser.add_argument("--harness", choices=["auto", "dsh", "claude", "codex", "mock"], default="auto",
                        help="harness to use; auto probes dsh > claude > codex (default: auto)")
    parser.add_argument("--mock", action="store_true", help="shortcut for --harness mock (offline deterministic scorer)")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help=f"runs per query (default: {DEFAULT_RUNS}; mock always 1)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help=f"per-call subprocess timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT, help="harness probe timeout in seconds")
    parser.add_argument("--queries", type=Path, default=None, help="trigger JSON (default: <kit-root>/evals/trigger.json)")
    parser.add_argument("--kit-root", type=Path, default=DEFAULT_KIT_ROOT, help="kit to install/evaluate (default: repo kit)")
    parser.add_argument("--kit-label", default=None, help="label for the kit under test, e.g. baseline-main-85f27c7")
    parser.add_argument("--limit", type=int, default=0, help="only run the first N queries (quick CI smoke)")
    parser.add_argument("--filter", default=None, help="comma-separated query ids to run")
    parser.add_argument("--fail-below", type=float, default=DEFAULT_THRESHOLD, help=f"failure threshold for exit code (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--json", action="store_true", help="print the machine-readable report to stdout (logs go to stderr)")
    parser.add_argument("--out", type=Path, default=None, help="write the JSON report to this path")
    parser.add_argument("--keep-scratch", action="store_true", help="keep the scratch project for inspection")
    parser.add_argument("--no-install", action="store_true", help="reuse --kit-root cwd instead of installing into a scratch project")
    parser.add_argument("--verbose", "-v", action="store_true", help="per-run progress on stderr")
    return parser


def resolve_harness(args: argparse.Namespace, kit_root: Path, probe_cwd: Path, env: dict, limitations: list[str]) -> tuple[Harness, dict, dict | None]:
    """Resolve the harness, probing with fallback for --harness auto."""
    requested = "mock" if args.mock else args.harness
    selection: dict = {"requested": requested, "resolved": None, "probe": [], "fallback": None}
    if requested == "mock":
        harness = MockHarness(load_skill_descriptions(kit_root))
        selection["resolved"] = "mock"
        return harness, selection, None

    candidates = ["dsh", "claude", "codex"] if requested == "auto" else [requested]
    last_error: str | None = None
    for name in candidates:
        try:
            harness = {"dsh": DshHarness, "claude": ClaudeHarness, "codex": CodexHarness}[name]()
        except HarnessError as exc:
            selection["probe"].append({"harness": name, "ok": False, "detail": str(exc)})
            last_error = str(exc)
            continue
        probe = harness.probe(probe_cwd, env, args.probe_timeout)
        selection["probe"].append(probe)
        if probe.get("ok"):
            selection["resolved"] = name
            return harness, selection, None
        last_error = str(probe.get("detail") or "probe failed")
    # No harness works: never fabricate. Fall back to the deterministic mock and say so.
    limitations.append(
        "No real harness passed its probe; fell back to the deterministic mock keyword scorer. "
        f"Last harness error: {last_error}. Real triggering evidence is NOT available in this run."
    )
    selection["fallback"] = {"to": "mock", "reason": last_error}
    eprint(f"warning: no real harness available ({last_error}); falling back to --mock")
    harness = MockHarness(load_skill_descriptions(kit_root))
    selection["resolved"] = "mock"
    return harness, selection, selection["fallback"]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kit_root = args.kit_root.resolve()
    queries_path = (args.queries or (kit_root / "evals" / "trigger.json")).resolve()
    if not queries_path.is_file():
        eprint(f"error: trigger set not found: {queries_path}")
        return 2
    if not (kit_root / "skills").is_dir():
        eprint(f"error: --kit-root does not look like the kit (no skills/): {kit_root}")
        return 2
    if args.runs < 1:
        eprint("error: --runs must be >= 1")
        return 2
    queries = load_queries(queries_path)
    if args.filter:
        wanted = {item.strip().upper() for item in args.filter.split(",") if item.strip()}
        queries = [query for query in queries if query["id"].upper() in wanted]
    if args.limit > 0:
        queries = queries[: args.limit]
    if not queries:
        eprint("error: no queries selected")
        return 2

    limitations: list[str] = []
    harness: Harness
    selection: dict = {}
    scratch: Path | None = None
    install_info: dict | None = None
    env: dict | None = None
    requested = "mock" if args.mock else args.harness
    try:
        if requested == "mock":
            harness = MockHarness(load_skill_descriptions(kit_root))
            selection = {"requested": "mock", "resolved": "mock", "probe": [], "fallback": None}
        elif args.no_install:
            harness = {"dsh": DshHarness, "claude": ClaudeHarness, "codex": CodexHarness}[requested]()
            selection = {"requested": requested, "resolved": requested, "probe": [], "fallback": None}
            scratch = None
        else:
            # Probe in a prepared scratch project so the probe exercises the installed kit.
            scratch, env, install_info = prepare_scratch(kit_root, args.keep_scratch)
            harness, selection, _ = resolve_harness(args, kit_root, scratch, env, limitations)
    except HarnessError as exc:
        eprint(f"error: {exc}")
        return 2

    runs = 1 if harness.name == "mock" or args.mock else args.runs
    if harness.name == "mock" and args.runs > 1:
        limitations.append("mock mode is deterministic; --runs > 1 is collapsed to 1 run.")
    eprint(
        f"trigger eval: {len(queries)} queries | harness={harness.name} (requested {selection.get('requested')}) "
        f"| runs/query={runs} | timeout={args.timeout:.0f}s | kit={args.kit_label or kit_root}"
    )
    if install_info:
        eprint(f"  installed kit into scratch: {scratch} (install.sh rc={install_info['returncode']})")
    coverage = description_coverage(kit_root)
    eprint(
        f"  description coverage: {coverage['with_use_when']}/{coverage['skills']} with 'Use when', "
        f"{coverage['with_negative_trigger']}/{coverage['skills']} with a negative trigger"
    )
    try:
        result = evaluate(queries, harness, runs=runs, timeout=args.timeout, scratch=scratch or Path.cwd(),
                          env=env, verbose=args.verbose)
    finally:
        if scratch is not None and not args.keep_scratch:
            shutil.rmtree(scratch, ignore_errors=True)

    report = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "kit_root": str(kit_root),
        "kit_label": args.kit_label,
        "kit_commit": _git_commit(kit_root),
        "harness": selection,
        "mock": harness.name == "mock",
        "runs_per_query": runs,
        "timeout_s": args.timeout,
        "mocked": harness.name == "mock",
        "queries_file": str(queries_path),
        "install": install_info,
        "description_coverage": coverage,
        "summary": result["summary"],
        "wrong_skill_matrix": result["wrong_skill_matrix"],
        "queries": result["queries"],
        "limitations": limitations,
    }
    summary = result["summary"]
    eprint(
        f"\nresult: {summary['passed']}/{summary['total']} passed "
        f"(accuracy={summary['accuracy']:.1%}, precision={summary['precision']:.1%}, "
        f"recall={summary['recall']:.1%}; should-trigger {summary['should_trigger']['passed']}/{summary['should_trigger']['total']}, "
        f"near-miss {summary['near_miss']['passed']}/{summary['near_miss']['total']}, "
        f"negative {summary['negative']['passed']}/{summary['negative']['total']})"
    )
    if result["wrong_skill_matrix"]:
        eprint("  failures:")
        for row in result["wrong_skill_matrix"]:
            eprint(f"    {row['id']}: expected {row['expected'] or 'none'}, observed {row['observed'] or 'none'} ({row['category']})")
    eprint(
        f"  avg {summary['avg_duration_s']:.1f}s/call; approx tokens: {summary['total_tokens']}"
        + (f"; mock heuristic (no model invoked)" if harness.name == "mock" else "")
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        eprint(f"  report written: {args.out}")
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    passed = summary["accuracy"] >= args.fail_below
    if not passed:
        eprint(f"FAIL: accuracy {summary['accuracy']:.1%} < threshold {args.fail_below:.0%}")
        return 1
    eprint(f"PASS: accuracy {summary['accuracy']:.1%} >= threshold {args.fail_below:.0%}")
    return 0


def _git_commit(kit_root: Path) -> str | None:
    rc, out, _, _, _ = run_process(["git", "-C", str(kit_root), "rev-parse", "HEAD"], cwd=kit_root, timeout=10)
    return out.strip() if rc == 0 else None


if __name__ == "__main__":
    sys.exit(main())
