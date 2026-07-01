from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.modules.data_contract.core.cache.contract_cache_scope import ContractCacheScope
from core.modules.data_contract.core.registry.contract_const import ContractScope, ContractType, DataKey


@dataclass(frozen=True)
class ContractInfo:
    """``info(data_key)`` 返回的 mapping 静态信息。"""

    data_key: DataKey
    scope: ContractScope
    contract_type: ContractType
    display_name: str
    loader_name: str
    defaults: dict[str, Any]
    unique_keys: list[str]
    has_cache: bool
    time_axis_field: str | None
    time_axis_format: str | None
    supports_start_end: bool
    cache_scope: ContractCacheScope


@dataclass(frozen=True)
class TimeRange:
    start: str
    end: str


@dataclass(frozen=True)
class UntilResult:
    rows: list[dict[str, Any]]
    as_of: str
