from __future__ import annotations

from enum import Enum


class ContractScope(str, Enum):
    """Contract scope (fixed by contract type, not user-provided)."""

    GLOBAL = "global"
    PER_ENTITY = "per_entity"
    PER_CATEGORY = "per_category"

