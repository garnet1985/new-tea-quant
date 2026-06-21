"""Lazy imports for data source BFF stack."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

_stack: Optional[SimpleNamespace] = None


def get_data_source_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    from core.modules.data_source.launcher import (
        fetch_data_source_catalog_page,
        fetch_data_source_freshness,
    )

    _stack = SimpleNamespace(
        fetch_data_source_catalog_page=fetch_data_source_catalog_page,
        fetch_data_source_freshness=fetch_data_source_freshness,
    )
    return _stack
