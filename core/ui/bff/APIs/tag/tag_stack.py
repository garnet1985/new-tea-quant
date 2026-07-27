"""Lazy imports for tag BFF stack."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

_stack: Optional[SimpleNamespace] = None


def get_tag_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    from core.modules.tag.core.bff_support import TagCatalog, TagRunLauncher

    _stack = SimpleNamespace(
        fetch_discovered_tags_page=TagCatalog.fetch_page,
        trigger_tag_run=TagRunLauncher.trigger,
        get_tag_run_progress=TagRunLauncher.get_progress,
    )
    return _stack
