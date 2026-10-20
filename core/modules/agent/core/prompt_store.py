"""Load model-facing prompt text from ``prompts/*.md`` (md only, no Python constants)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping, Optional

# core/prompt_store.py → agent/
_PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"
_SECTION_RE = re.compile(r"^##\s+(\S+)\s*$", re.MULTILINE)
_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def prompts_root() -> Path:
    return _PROMPTS_ROOT


def load_prompt(rel_path: str, *, variables: Optional[Mapping[str, str]] = None) -> str:
    """Load ``prompts/<rel_path>`` and substitute ``{{name}}`` placeholders."""
    text = _read_file(rel_path)
    if not variables:
        return text
    return _substitute(text, variables)


def load_section(rel_path: str, key: str) -> str:
    """Load a ``## key`` section from a multi-section markdown file."""
    sections = _sections(rel_path)
    needle = str(key or "").strip()
    body = sections.get(needle)
    if body is None:
        raise KeyError(f"prompt section not found: {rel_path}##{needle}")
    return body


def load_reply(key: str, *, variables: Optional[Mapping[str, str]] = None) -> str:
    text = load_section("replies.md", key)
    if not variables:
        return text
    return _substitute(text, variables)


def load_nudge(role: str, key: str, *, variables: Optional[Mapping[str, str]] = None) -> str:
    role_key = str(role or "").strip()
    if role_key not in {"worker", "guide"}:
        raise KeyError(f"unknown nudge role: {role_key}")
    text = load_section(f"nudges/{role_key}.md", key)
    if not variables:
        return text
    return _substitute(text, variables)


def _read_file(rel_path: str) -> str:
    rel = str(rel_path or "").strip().lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise ValueError(f"invalid prompt path: {rel_path!r}")
    path = (_PROMPTS_ROOT / rel).resolve()
    try:
        path.relative_to(_PROMPTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"prompt path escapes root: {rel_path!r}") from exc
    if not path.is_file():
        raise FileNotFoundError(f"prompt file missing: {rel}")
    return path.read_text(encoding="utf-8").strip() + "\n"


@lru_cache(maxsize=64)
def _sections(rel_path: str) -> Dict[str, str]:
    text = _read_file(rel_path)
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return {}
    out: Dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        out[match.group(1)] = text[start:end].strip()
    return out


def _substitute(text: str, variables: Mapping[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            raise KeyError(f"prompt variable missing: {{{{{name}}}}}")
        return str(variables[name])

    return _VAR_RE.sub(repl, text)
