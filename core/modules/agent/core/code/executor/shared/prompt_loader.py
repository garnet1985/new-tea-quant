"""从 ``core/content/`` 加载文案（md/txt only；禁止在 code 里堆大段中文）。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

# shared → executor → code → core → content/
_CONTENT_ROOT = Path(__file__).resolve().parents[3] / "content"
_SECTION_RE = re.compile(r"^##\s+(\S+)\s*$", re.MULTILINE)
_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

_REPLY_FILES: Tuple[str, ...] = (
    "global/whoiam.md",
    "global/responsibility.md",
    "specific/navigator/replies.md",
    "specific/guider/replies.md",
)

_NUDGE_FILES = {
    "guide": "specific/guider/nudges.md",
    "worker": "specific/worker/nudges.md",
}


def content_root() -> Path:
    return _CONTENT_ROOT


def prompts_root() -> Path:
    """兼容旧名：现为 content 根。"""
    return _CONTENT_ROOT


def load_prompt(rel_path: str, *, variables: Optional[Mapping[str, str]] = None) -> str:
    """Load ``content/<rel_path>`` and substitute ``{{name}}`` placeholders."""
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
    text = _load_section_from(_REPLY_FILES, key)
    if not variables:
        return text
    return _substitute(text, variables)


def load_nudge(role: str, key: str, *, variables: Optional[Mapping[str, str]] = None) -> str:
    role_key = str(role or "").strip()
    rel = _NUDGE_FILES.get(role_key)
    if not rel:
        raise KeyError(f"unknown nudge role: {role_key}")
    text = load_section(rel, key)
    if not variables:
        return text
    return _substitute(text, variables)


def _load_section_from(rel_paths: Sequence[str], key: str) -> str:
    needle = str(key or "").strip()
    for rel in rel_paths:
        sections = _sections(rel)
        if needle in sections:
            return sections[needle]
    raise KeyError(f"reply section not found: {needle}")


def _read_file(rel_path: str) -> str:
    rel = str(rel_path or "").strip().lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise ValueError(f"invalid content path: {rel_path!r}")
    path = (_CONTENT_ROOT / rel).resolve()
    try:
        path.relative_to(_CONTENT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"content path escapes root: {rel_path!r}") from exc
    if not path.is_file():
        raise FileNotFoundError(f"content file missing: {rel}")
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
