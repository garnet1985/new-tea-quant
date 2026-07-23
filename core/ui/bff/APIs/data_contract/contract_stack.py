"""Lazy imports for data contract BFF stack."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

_stack: Optional[SimpleNamespace] = None


def get_data_contract_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    from core.modules.data_contract.core.launcher import fetch_data_contract_catalog_page

    _stack = SimpleNamespace(
        fetch_data_contract_catalog_page=fetch_data_contract_catalog_page,
    )
    return _stack
