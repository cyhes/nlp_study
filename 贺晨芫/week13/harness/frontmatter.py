"""Minimal, dependency-free YAML frontmatter parser + text tokenization.

Skills store metadata as YAML frontmatter at the top of ``SKILL.md``. We only
need a small, predictable subset (scalar values + simple lists), so we avoid a
hard dependency on PyYAML and keep the harness runnable with the standard
library alone.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_WORD_RE = re.compile(r"[a-z0-9_]+")


class Frontmatter:
    """Parsed result of a markdown document with leading frontmatter."""

    def __init__(self, data: dict[str, Any], body: str):
        self.data = data
        self.body = body

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


def _coerce(val: str) -> Any:
    low = val.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", "~"):
        return None
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    if re.fullmatch(r"-?\d+\.\d+", val):
        return float(val)
    return val


def parse_frontmatter(text: str) -> Frontmatter:
    """Parse a document with leading YAML frontmatter.

    Returns ``Frontmatter`` with ``data`` (dict) and ``body`` (markdown after
    the closing ``---``). If no frontmatter is present, ``data`` is empty and
    the whole text is treated as the body.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return Frontmatter({}, text)

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return Frontmatter({}, text)

    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:])
    data: dict[str, Any] = {}
    current_key: str | None = None
    list_mode = False

    for raw in fm_lines:
        if not raw.strip():
            continue
        if raw.startswith("- ") and current_key is not None:
            if not isinstance(data.get(current_key), list):
                data[current_key] = (
                    [data[current_key]] if current_key in data else []
                )
            data[current_key].append(_coerce(raw[2:].strip()))
            list_mode = True
            continue
        if ":" in raw:
            key, _, val = raw.partition(":")
            key = key.strip()
            val = val.strip()
            current_key = key
            list_mode = False
            if val == "":
                data[key] = []  # placeholder; may become a list via "- " lines
            else:
                data[key] = _coerce(val)
        elif list_mode and current_key is not None:
            data[current_key].append(_coerce(raw.strip()))

    for k, v in list(data.items()):
        if v == []:
            data[k] = None
    return Frontmatter(data, body)


def parse_frontmatter_file(path: Path) -> Frontmatter:
    return parse_frontmatter(Path(path).read_text(encoding="utf-8"))


def parse_frontmatter_head(path: Path, max_lines: int = 80) -> dict[str, Any]:
    """Parse *only* the frontmatter block, without reading the full body.

    This is the Level-1 (metadata-only) discovery path: cheap, bounded I/O,
    so building the index of hundreds of skills stays fast.
    """
    with open(path, "r", encoding="utf-8") as fh:
        lines = []
        for i, line in enumerate(fh):
            lines.append(line)
            if i >= max_lines:
                break
    return parse_frontmatter("".join(lines)).data


def tokenize(text: str) -> set[str]:
    """Tokenize text for routing: latin words + CJK bigrams.

    CJK bigrams capture short-phrase overlap without a full segmenter, which
    is enough for matching a query against skill descriptions/names.
    """
    text = (text or "").lower()
    tokens: set[str] = set()
    for m in _WORD_RE.findall(text):
        if len(m) > 1:
            tokens.add(m)
    for m in _CJK_RE.findall(text):
        if len(m) == 1:
            tokens.add(m)
        else:
            for i in range(len(m) - 1):
                tokens.add(m[i : i + 2])
    return tokens
