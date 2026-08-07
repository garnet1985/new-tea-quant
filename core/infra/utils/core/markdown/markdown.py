"""Markdown template filler — replace ``{{:token}}`` placeholders.

Usage::

    mgr = MarkdownMgr.load_template("REPORT_TEMPLATE.md")
    mgr.fill("wall_clock_seconds", "3s")
    mgr.save("out/REPORT.md")
    mgr.clear()  # drop fills; template text restored
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

# {{:token_name}} — colon marks template slots; plain {{x}} left alone for MD/IDE.
_TOKEN_RE = re.compile(r"\{\{:([A-Za-z_][A-Za-z0-9_]*)\}\}")


def _normalize_content(content: Any) -> str:
    """Only real ``str`` is kept; ``None`` / other types → ``\"\"``."""
    if isinstance(content, str):
        return content
    return ""


def _normalize_token_name(token: str) -> str:
    name = str(token or "").strip()
    if name.startswith("{{:") and name.endswith("}}"):
        name = name[3:-2].strip()
    elif name.startswith("{{") and name.endswith("}}"):
        name = name[2:-2].lstrip(":").strip()
    if not name:
        raise ValueError("token 名不能为空")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"非法 token 名: {token!r}")
    return name


class MarkdownMgr:
    """Load an MD template, fill ``{{:token}}`` slots, save the result."""

    def __init__(self, template_content: str, *, source_path: Optional[Path] = None):
        self._template_content = str(template_content if template_content is not None else "")
        self._source_path = Path(source_path).resolve() if source_path is not None else None
        self._token_names = MarkdownMgr.extract_tokens(self._template_content)
        self._values: Dict[str, str] = {}

    # ── load template ──

    @classmethod
    def load_template(cls, path: Union[str, Path]) -> "MarkdownMgr":
        """Load template from a markdown file path."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"markdown template not found: {p}")
        text = p.read_text(encoding="utf-8")
        return cls(text, source_path=p)

    @classmethod
    def from_text(cls, template_content: str) -> "MarkdownMgr":
        """Load template from an in-memory string (no file)."""
        return cls(template_content, source_path=None)

    @staticmethod
    def extract_tokens(template: str) -> List[str]:
        """Ordered unique token names appearing in ``template``."""
        seen: Dict[str, None] = {}
        for m in _TOKEN_RE.finditer(template or ""):
            seen.setdefault(m.group(1), None)
        return list(seen.keys())

    # ── inspect ──

    @property
    def source_path(self) -> Optional[Path]:
        return self._source_path

    @property
    def template_content(self) -> str:
        return self._template_content

    @property
    def tokens(self) -> List[str]:
        """Token names discovered in the template (no ``{{:}}`` wrapper)."""
        return list(self._token_names)

    @property
    def values(self) -> Dict[str, str]:
        """Copy of filled values (token name → content)."""
        return dict(self._values)

    # ── fill ──

    def fill(self, token: str, content: Any) -> "MarkdownMgr":
        """Set one token; later fills overwrite earlier ones."""
        name = _normalize_token_name(token)
        self._values[name] = _normalize_content(content)
        return self

    def fill_many(self, mapping: Mapping[str, Any]) -> "MarkdownMgr":
        """Fill multiple tokens (same overwrite rules as ``fill``)."""
        for key, value in dict(mapping or {}).items():
            self.fill(str(key), value)
        return self

    def clear(self) -> "MarkdownMgr":
        """Drop filled values; template text unchanged."""
        self._values = {}
        return self

    # ── render / save ──

    def missing_tokens(self) -> List[str]:
        """Template tokens that have not been filled yet."""
        return [t for t in self._token_names if t not in self._values]

    def render(self) -> str:
        """Apply fills; raise if any template token is missing."""
        missing = self.missing_tokens()
        if missing:
            raise ValueError(
                "markdown template 尚有未填 token: " + ", ".join(missing)
            )
        return _TOKEN_RE.sub(
            lambda m: self._values.get(m.group(1), m.group(0)),
            self._template_content,
        )

    def save(self, path: Union[str, Path]) -> Path:
        """Render and write UTF-8 markdown; return resolved output path."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        text = self.render()
        out.write_text(text, encoding="utf-8")
        return out.resolve()


__all__ = ["MarkdownMgr"]
