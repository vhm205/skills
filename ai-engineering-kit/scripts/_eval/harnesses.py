"""Shared coding-harness adapters. Capabilities describe observation, not guarantees."""
from __future__ import annotations
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from .process import run_process

which = shutil.which
SKILL_NAME_RE = re.compile(r"[a-z][a-z0-9-]*")
DECLARED_RE = re.compile(r"(?im)^\s*[-*`> ]*SKILL_USED\s*:\s*(?P<names>.*?)\s*$")
NONE_WORDS = {"none", "no", "nothing", "null", "-", "n/a", "na", "no skill", "no skills"}


def normalized_usage(raw: dict) -> dict:
    result = {}
    for source, target in (("totalTokens", "total_tokens"), ("outputTokens", "output_tokens"),
                           ("inputTokens", "input_tokens"), ("cachedInputTokens", "cached_input_tokens"),
                           ("cacheReadTokens", "cache_read_tokens"), ("cacheWriteTokens", "cache_write_tokens")):
        if type(raw.get(source)) is int and raw[source] >= 0:
            result[target] = raw[source]
    return result


def describe(name: str) -> dict:
    binary = which(name)
    version = None
    if binary:
        rc, out, _, _, _ = run_process([binary, "--version"], cwd=Path.cwd(), timeout=10)
        if rc == 0:
            version = out.strip()[:160]
    result = {"name": name, "binary_available": bool(binary), "version": version,
            "capabilities": {"headless": bool(binary), "fresh_session": True,
                             "skill_events": name == "dsh", "tool_events": name == "dsh",
                             "usage": True, "grader_isolation": False,
                             "global_config_isolation": False},
            "limitations": ["Fresh working directory is not a process sandbox.",
                            "Global configuration and model pinning require a verified adapter."]}
    if name == "dsh" and binary:
        from .dsh import capabilities, authentication_available
        result["capabilities"].update(capabilities(binary))
        result["capabilities"]["authentication"] = authentication_available(binary)
        result["limitations"] = ["macOS sandbox capability probes are local; Linux requires an isolated runner adapter.",
                                 "DSH official provider only; no custom global plugins or settings are loaded.",
                                 "Model patch pins requested identity; provider-returned model identity may be unavailable."]
    return result

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
    raw_stdout: str = ""
    raw_stderr: str = ""
    events: list[dict] = field(default_factory=list)


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
        events: list[dict] = []
        malformed = False
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            raw_lines += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed = True
                continue
            if not isinstance(event, dict):
                continue
            events.append(event)
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
            elif etype == "status" and (event.get("phase") == "step_end" or event.get("usage")):
                usage_steps.append(event.get("usage") or {})
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
        if not events or malformed:
            error = "harness produced no JSON events"
        elif errors:
            error = "harness error: " + "; ".join(errors[:2])
        return HarnessResult(
            skills_used=resolved,
            source=source,
            text=combined,
            duration_s=duration_s,
            usage=usage,
            error=error,
            raw_excerpt=(stdout or stderr)[-1200:],
            raw_stdout=stdout, raw_stderr=stderr, events=events,
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
        elif rc != 0:
            result.error = f"harness exited {rc}: {(err or out).strip()[-800:]}"
        result.raw_stdout, result.raw_stderr = out, err
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
            if isinstance(usage, dict) and "input_tokens" in usage and "output_tokens" in usage:
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
        elif rc != 0:
            result.error = f"claude exited {rc}: {(err or out).strip()[-800:]}"
        result.raw_stdout, result.raw_stderr = out, err
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
        events: list[dict] = []
        stream_errors: list[str] = []
        malformed = False
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed = True
                continue
            if not isinstance(event, dict):
                continue
            events.append(event)
            etype = event.get("type")
            if etype in ("error", "turn.failed"):
                stream_errors.append(str(event.get("error") or event.get("message") or "turn failed"))
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
            events=events,
        )
        if malformed or not events:
            result.error = "codex produced an invalid or empty JSON stream"
        elif stream_errors:
            result.error = "; ".join(stream_errors)[:800]
        if rc is None:
            result.error = (err.strip() or "timeout")[-800:]
        elif rc != 0:
            result.error = f"codex exited {rc}: {(err or out).strip()[-800:]}"
        result.raw_stdout, result.raw_stderr = out, err
        return result

    def probe(self, cwd: Path, env: dict[str, str] | None, timeout: float) -> dict:
        result = self.run("Reply with exactly: PROBE_OK", cwd, env, timeout)
        ok = False if result.error else bool(re.search(r"PROBE_OK", result.text))
        return {
            "harness": "codex",
            "ok": ok,
            "detail": "probe returned PROBE_OK" if ok else (result.error or "no PROBE_OK in output")[-500:],
        }


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _sum_usage(steps: list[dict]) -> dict:
    if not steps:
        return {}
    if any("totalTokens" not in step for step in steps):
        return {}
    result = {"steps": len(steps)}
    for key in ("totalTokens", "inputTokens", "outputTokens", "cacheReadTokens", "cacheWriteTokens"):
        if all(type(step.get(key)) is int and step[key] >= 0 for step in steps):
            result[key] = sum(step[key] for step in steps)
    return result


