"""Minimal YAML frontmatter reader for ``.aiek/adapter.md`` — Python 3.9+ stdlib only.

The kit cannot assume PyYAML in an installed project, so the adapter frontmatter is read
with this deliberately tiny parser. It supports exactly the shape described in
``core/adapter-contract.md``:

* mappings nested by indentation (spaces only, two-space style preferred),
* block sequences (``- item``), including sequences of scalars and of mappings,
* inline sequences of scalars (``[]``, ``[a, b]``),
* plain, single-quoted and double-quoted scalars,
* ``null`` / ``~`` and ``true`` / ``false``,
* blank lines and ``#`` comments (inline comments only when preceded by whitespace).

Anything outside that subset (tabs, inline mappings, block scalars, anchors, duplicate
keys, inconsistent indentation) fails with a ``file:line: message`` error instead of being
silently mis-parsed: an adapter that means something different than the agent thinks is a
safety issue, not a formatting nit.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "FrontmatterError",
    "get",
    "load_adapter",
    "parse_frontmatter",
    "parse_frontmatter_document",
]

_TRUE = frozenset(("true", "True", "TRUE"))
_FALSE = frozenset(("false", "False", "FALSE"))
_NULL = frozenset(("null", "Null", "NULL", "~"))

_ESCAPE_MAP = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "0": "\x00",
    "b": "\b",
    "f": "\f",
}


class FrontmatterError(ValueError):
    """A parse or IO error in an adapter YAML frontmatter.

    The message is prefixed with ``path:line:`` when both are known so every error can be
    acted on without opening the file.
    """

    def __init__(self, message, path=None, line=None):
        self.message = message
        self.path = str(path) if path is not None else None
        self.line = line
        if self.path and line:
            prefix = "%s:%d: " % (self.path, line)
        elif self.path:
            prefix = "%s: " % self.path
        elif line:
            prefix = "line %d: " % line
        else:
            prefix = ""
        super().__init__(prefix + message)


class _Token:
    __slots__ = ("indent", "line", "text")

    def __init__(self, indent, line, text):
        self.indent = indent
        self.line = line
        self.text = text

    def __repr__(self):  # pragma: no cover - debugging aid
        return "_Token(indent=%r, line=%r, text=%r)" % (self.indent, self.line, self.text)


def _err(path, line, message):
    return FrontmatterError(message, path, line)


def _strip_comment(text):
    """Remove a trailing ``#`` comment, respecting quoted scalars."""
    quote = None
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if quote == '"':
            if char == "\\":
                i += 2
                continue
            if char == '"':
                quote = None
        elif quote == "'":
            if char == "'":
                if i + 1 < length and text[i + 1] == "'":
                    i += 2
                    continue
                quote = None
        else:
            if char in "\"'":
                quote = char
            elif char == "#" and (i == 0 or text[i - 1] in " \t"):
                return text[:i].rstrip()
        i += 1
    return text.rstrip()


def _tokenize(frontmatter, path, first_line):
    tokens = []
    for index, raw in enumerate(frontmatter.splitlines()):
        line = first_line + index
        if not raw.strip():
            continue
        stripped = raw.rstrip()
        body = stripped.lstrip(" \t")
        indent_text = stripped[: len(stripped) - len(body)]
        if "\t" in indent_text:
            raise _err(path, line, "tab character in indentation; use spaces")
        if not body or body.startswith("#"):
            continue
        content = _strip_comment(body).rstrip()
        if not content:
            continue
        tokens.append(_Token(len(indent_text), line, content))
    return tokens


def _parse_double_quoted(text, path, line):
    chars = []
    index = 1
    end = len(text) - 1
    while index < end:
        char = text[index]
        if char != "\\":
            chars.append(char)
            index += 1
            continue
        index += 1
        if index >= end:
            raise _err(path, line, "dangling escape at end of double-quoted scalar")
        escape = text[index]
        if escape in _ESCAPE_MAP:
            chars.append(_ESCAPE_MAP[escape])
            index += 1
            continue
        if escape in ("u", "x"):
            size = 4 if escape == "u" else 2
            digits = text[index + 1 : index + 1 + size]
            if len(digits) != size or not re.fullmatch(r"[0-9a-fA-F]+", digits):
                raise _err(
                    path,
                    line,
                    "invalid \\%s escape in double-quoted scalar: expected %d hex digits"
                    % (escape, size),
                )
            chars.append(chr(int(digits, 16)))
            index += 1 + size
            continue
        raise _err(
            path,
            line,
            "unsupported escape \\%s in double-quoted scalar" % escape,
        )
    return "".join(chars)


def _split_inline_items(inner, path, line):
    parts = []
    buffer = []
    quote = None
    index = 0
    length = len(inner)
    while index < length:
        char = inner[index]
        if quote == '"':
            buffer.append(char)
            if char == "\\" and index + 1 < length:
                index += 1
                buffer.append(inner[index])
            elif char == '"':
                quote = None
        elif quote == "'":
            buffer.append(char)
            if char == "'":
                if index + 1 < length and inner[index + 1] == "'":
                    index += 1
                    buffer.append(inner[index])
                else:
                    quote = None
        elif char in "\"'":
            quote = char
            buffer.append(char)
        elif char == ",":
            parts.append("".join(buffer))
            buffer = []
        else:
            buffer.append(char)
        index += 1
    if quote:
        raise _err(path, line, "unterminated quoted scalar in inline sequence")
    parts.append("".join(buffer))
    items = []
    for part in parts:
        if not part.strip():
            raise _err(path, line, "empty item in inline sequence; remove the extra comma")
        items.append(part.strip())
    return items


def _parse_inline_sequence(text, path, line):
    if text == "[]":
        return []
    if not text.endswith("]"):
        raise _err(path, line, "unterminated inline sequence; expected ']'")
    inner = text[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(item, path, line) for item in _split_inline_items(inner, path, line)]


def _parse_scalar(text, path, line):
    text = text.strip()
    if not text or text == "~":
        return None
    first = text[0]
    if first == '"':
        if len(text) < 2 or text[-1] != '"':
            raise _err(
                path,
                line,
                "unterminated double-quoted scalar; close the quote at the end of the line",
            )
        return _parse_double_quoted(text, path, line)
    if first == "'":
        if len(text) < 2 or text[-1] != "'":
            raise _err(
                path,
                line,
                "unterminated single-quoted scalar; close the quote at the end of the line",
            )
        return text[1:-1].replace("''", "'")
    if text in _NULL:
        return None
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    if text.startswith("["):
        return _parse_inline_sequence(text, path, line)
    if text.startswith("{"):
        if text == "{}":
            return {}
        raise _err(
            path,
            line,
            "inline mappings are not supported in adapter frontmatter; use one key per line",
        )
    if text.startswith("|") or text.startswith(">"):
        raise _err(
            path,
            line,
            "block scalars (| or >) are not supported in adapter frontmatter; "
            "use a single-quoted or double-quoted scalar",
        )
    if text.startswith("&") or text.startswith("*"):
        raise _err(path, line, "YAML anchors/aliases are not supported in adapter frontmatter")
    if text.startswith(("- ", "? ", ": ")):
        raise _err(path, line, "unexpected YAML indicator at start of scalar")
    return text


def _find_unquoted_colon(text):
    """Return the index of the ``key:`` separator, or -1 when the line is not a mapping."""
    quote = None
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if quote == '"':
            if char == "\\":
                index += 2
                continue
            if char == '"':
                quote = None
        elif quote == "'":
            if char == "'":
                if index + 1 < length and text[index + 1] == "'":
                    index += 2
                    continue
                quote = None
        elif char in "\"'":
            quote = char
        elif char == ":" and (index + 1 == length or text[index + 1] in " \t"):
            return index
        index += 1
    return -1


def _split_key(text, path, line):
    if text[0] in "\"'":
        quote = text[0]
        index = 1
        close = -1
        while index < len(text):
            char = text[index]
            if quote == '"':
                if char == "\\":
                    index += 2
                    continue
                if char == '"':
                    close = index
                    break
            else:
                if char == "'":
                    if index + 1 < len(text) and text[index + 1] == "'":
                        index += 2
                        continue
                    close = index
                    break
            index += 1
        if close < 0:
            raise _err(path, line, "unterminated quoted mapping key")
        key = _parse_scalar(text[: close + 1], path, line)
        rest = text[close + 1 :]
        if not rest.startswith(":"):
            raise _err(path, line, "expected ':' after quoted mapping key")
        value = rest[1:]
        if value.startswith(" "):
            value = value[1:]
        return str(key), value.strip()
    colon = _find_unquoted_colon(text)
    if colon < 0:
        raise _err(
            path,
            line,
            "expected 'key: value' or 'key:' on its own line; missing ':'",
        )
    key = text[:colon].strip()
    if not key:
        raise _err(path, line, "empty mapping key")
    return key, text[colon + 1 :].strip()


def _is_sequence_indicator(text):
    return text == "-" or text.startswith("- ")


def _looks_like_mapping_entry(text, path, line):
    if not text:
        return False
    first = text[0]
    if first in "\"'":
        quote = first
        index = 1
        while index < len(text):
            char = text[index]
            if quote == '"':
                if char == "\\":
                    index += 2
                    continue
                if char == '"':
                    break
            elif char == "'":
                if char == "'":
                    if index + 1 < len(text) and text[index + 1] == "'":
                        index += 2
                        continue
                    break
            index += 1
        if index >= len(text):
            return False
        return text[index + 1 :].startswith(":")
    return _find_unquoted_colon(text) >= 0


def _parse_sequence(tokens, start, indent, path):
    items = []
    position = start
    total = len(tokens)
    while position < total:
        token = tokens[position]
        if token.indent != indent or not _is_sequence_indicator(token.text):
            break
        after = token.text[1:]
        rest = after.strip()
        position += 1
        body = []
        while position < total and tokens[position].indent > indent:
            body.append(tokens[position])
            position += 1
        if not rest:
            if not body:
                items.append(None)
            else:
                value, consumed = _parse_node(body, 0, body[0].indent, path)
                if consumed != len(body):
                    raise _err(
                        path,
                        body[consumed].line,
                        "unexpected content in sequence item",
                    )
                items.append(value)
            continue
        if not _looks_like_mapping_entry(rest, path, token.line):
            if body:
                raise _err(
                    path,
                    body[0].line,
                    "unexpected indented content after sequence item '%s'" % rest,
                )
            items.append(_parse_scalar(rest, path, token.line))
            continue
        spaces = len(after) - len(after.lstrip())
        virtual_indent = indent + 1 + spaces
        entry = [_Token(virtual_indent, token.line, rest)]
        if body and body[0].indent < virtual_indent:
            raise _err(
                path,
                body[0].line,
                "inconsistent indentation inside sequence item: expected at least %d spaces"
                % virtual_indent,
            )
        combined = entry + body
        value, consumed = _parse_node(combined, 0, virtual_indent, path)
        if consumed != len(combined):
            raise _err(
                path,
                combined[consumed].line,
                "unexpected content in sequence item",
            )
        items.append(value)
    return items, position


def _parse_mapping(tokens, start, indent, path):
    mapping = {}
    first_lines = {}
    position = start
    total = len(tokens)
    while position < total:
        token = tokens[position]
        if token.indent < indent:
            break
        if token.indent > indent:
            raise _err(
                path,
                token.line,
                "unexpected indentation: expected %d spaces, found %d"
                % (indent, token.indent),
            )
        if _is_sequence_indicator(token.text):
            raise _err(
                path,
                token.line,
                "unexpected '-' sequence item where a 'key: value' mapping entry was expected",
            )
        key, value_text = _split_key(token.text, path, token.line)
        if key in mapping:
            raise _err(
                path,
                token.line,
                "duplicate key '%s' (first defined on line %d)"
                % (key, first_lines.get(key, token.line)),
            )
        first_lines[key] = token.line
        position += 1
        if value_text:
            mapping[key] = _parse_scalar(value_text, path, token.line)
        elif position < total and tokens[position].indent > indent:
            mapping[key], position = _parse_node(
                tokens, position, tokens[position].indent, path
            )
        else:
            mapping[key] = None
    return mapping, position


def _parse_node(tokens, start, indent, path):
    if _is_sequence_indicator(tokens[start].text):
        return _parse_sequence(tokens, start, indent, path)
    return _parse_mapping(tokens, start, indent, path)


def parse_frontmatter_document(text, path="<adapter>"):
    """Split a markdown document into parsed frontmatter and prose.

    Returns a dict with keys ``data`` (the parsed mapping), ``prose`` (everything after the
    closing ``---``), and ``body_start_line`` (1-based line number where prose starts).
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise _err(path, 1, "missing YAML frontmatter: the file must start with '---'")
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
    if closing is None:
        raise _err(
            path,
            len(lines),
            "unterminated YAML frontmatter: no closing '---' line",
        )
    frontmatter = "\n".join(lines[1:closing])
    prose = "\n".join(lines[closing + 1 :])
    tokens = _tokenize(frontmatter, path, first_line=2)
    data = {}
    if tokens:
        data, consumed = _parse_node(tokens, 0, tokens[0].indent, path)
        if consumed != len(tokens):
            raise _err(path, tokens[consumed].line, "unexpected content after frontmatter value")
        if not isinstance(data, dict):
            raise _err(path, 2, "frontmatter must be a mapping of keys to values")
    return {
        "data": data,
        "prose": prose,
        "body_start_line": closing + 2,
        "frontmatter_text": frontmatter,
    }


def parse_frontmatter(text, path="<adapter>"):
    """Parse only the frontmatter; returns ``(data, prose)``."""
    document = parse_frontmatter_document(text, path)
    return document["data"], document["prose"]


def load_adapter(path):
    """Read and parse an adapter file.

    Returns ``(data, meta)`` where ``meta`` holds ``path`` (absolute), ``prose``,
    ``body_start_line`` and the raw ``text``. Raises :class:`FrontmatterError` with a
    helpful message when the file is missing or invalid.
    """
    candidate = Path(path).expanduser()
    try:
        text = candidate.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FrontmatterError(
            "adapter file not found: %s (expected .aiek/adapter.md in the project)" % candidate,
            candidate,
        ) from None
    except IsADirectoryError:
        raise FrontmatterError(
            "adapter path is a directory, not a file: %s" % candidate, candidate
        ) from None
    except OSError as exc:
        raise FrontmatterError("cannot read adapter file: %s" % exc, candidate) from None
    document = parse_frontmatter_document(text, str(candidate))
    meta = {
        "path": str(candidate.resolve()),
        "prose": document["prose"],
        "body_start_line": document["body_start_line"],
        "text": text,
    }
    return document["data"], meta


def get(data, dotted, default=None):
    """Read a dotted key (``verify.test_fast``) from nested mappings."""
    value = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value
