"""Download filename helpers for strategy package export (BFF / CLI)."""

from __future__ import annotations

from typing import Tuple

BUNDLE_NAME_SUFFIX = "-strategy.zip"
_SINGLE_SUFFIX = {
    "strategy": "-strategy-only.zip",
    "tag": "-tag.zip",
    "adapter": "-adapter.zip",
}
_SINGLE_KINDS = frozenset(_SINGLE_SUFFIX)


def _sanitize_name(name: str) -> str:
    safe = str(name or "").strip()
    safe = safe.replace("/", "_").replace("\\", "_").replace(".", "-")
    return safe


def bundle_filename(strategy_name: str) -> str:
    return f"{_sanitize_name(strategy_name)}{BUNDLE_NAME_SUFFIX}"


def single_entity_filename(kind: str, name: str) -> str:
    k = str(kind or "").strip().lower()
    suffix = _SINGLE_SUFFIX.get(k)
    if not suffix:
        raise ValueError(f"unsupported single export kind: {kind!r}")
    return f"{_sanitize_name(name)}{suffix}"


def parse_export_target(raw: str) -> Tuple[str, str]:
    """
    Parse export target.

    Returns ``("bundle", strategy_name)`` or ``(kind, name)`` for single export
    when ``kind`` is one of ``strategy``, ``tag``, ``adapter``.
    """
    text = str(raw or "").strip()
    if not text:
        raise ValueError("export target is required")
    if ":" not in text:
        return "bundle", text
    kind, name = text.split(":", 1)
    kind = kind.strip().lower()
    name = name.strip()
    if kind not in _SINGLE_KINDS:
        raise ValueError(
            f"unknown export kind {kind!r}; use tag:NAME, adapter:NAME, strategy:NAME, "
            "or bare strategy bundle name"
        )
    if not name:
        raise ValueError(f"export target {text!r} requires a name after ':'")
    return kind, name


__all__ = [
    "bundle_filename",
    "parse_export_target",
    "single_entity_filename",
]
