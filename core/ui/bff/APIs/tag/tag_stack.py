"""Lazy imports for tag BFF stack."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

_stack: Optional[SimpleNamespace] = None


def get_tag_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    from core.modules.tag.launcher import (
        fetch_discovered_tags_page,
        get_tag_run_progress,
        trigger_tag_run,
    )

    _stack = SimpleNamespace(
        fetch_discovered_tags_page=fetch_discovered_tags_page,
        trigger_tag_run=trigger_tag_run,
        get_tag_run_progress=get_tag_run_progress,
    )
    return _stack
