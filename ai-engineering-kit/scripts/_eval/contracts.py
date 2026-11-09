"""Versioned eval contracts, validated without third-party dependencies."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

SCHEMAS = Path(__file__).parent / "schemas"
STATUSES = {"planned", "started", "completed", "timeout", "install-error", "auth-error",
            "harness-error", "grader-error", "unsupported", "interrupted"}


class ContractError(ValueError):
    """Invalid experiment input or incompatible evidence."""


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def _validate(schema: dict, value, at: str) -> None:
    kind = schema.get("type")
    if isinstance(kind, list):
        for option in kind:
            try:
                _validate({**schema, "type": option}, value, at)
                return
            except ContractError:
                pass
        raise ContractError(f"{at}: expected {kind}")
    checks = {"object": lambda: isinstance(value, dict), "array": lambda: isinstance(value, list),
              "string": lambda: isinstance(value, str), "boolean": lambda: type(value) is bool,
              "integer": lambda: type(value) is int,
              "number": lambda: type(value) in (int, float) and math.isfinite(value),
              "null": lambda: value is None}
    if kind and not checks[kind]():
        raise ContractError(f"{at}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{at}: value outside enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ContractError(f"{at}: missing {key}")
        for key, item in value.items():
            if key in schema.get("properties", {}):
                _validate(schema["properties"][key], item, f"{at}.{key}")
            elif schema.get("additionalProperties") is False:
                raise ContractError(f"{at}: unknown key {key}")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ContractError(f"{at}: too few items")
        if schema.get("uniqueItems") and len({digest(item) for item in value}) != len(value):
            raise ContractError(f"{at}: duplicate items")
        for index, item in enumerate(value):
            if "items" in schema:
                _validate(schema["items"], item, f"{at}[{index}]")
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ContractError(f"{at}: empty string")
    if type(value) in (int, float):
        if value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            raise ContractError(f"{at}: outside range")


def validate(name: str, value) -> None:
    _validate(json.loads((SCHEMAS / f"{name}.json").read_text()), value, name)


def validate_suite(suite: dict, *, planning: bool = False) -> None:
    validate("suite", suite)
    count = len(suite["scenarios"]) * len(suite["variants"]) * suite["repeats"]
    if count > suite["max_trials"]:
        raise ContractError(f"suite schedules {count} trials, exceeds max_trials={suite['max_trials']}")
    if not planning and suite["harness"] != "mock" and not suite.get("model"):
        raise ContractError("real execution requires an explicit model")


def validate_assertion(spec: dict) -> None:
    validate("assertion", spec)
    if spec["critical"] and spec["dimension"] not in ("safety", "outcome", "compliance"):
        raise ContractError("invalid critical assertion dimension")
