"""Data contract catalog for UI (read-only list)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.modules.data_contract.core.registry.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.core.registry.discovery import discover_userspace_map
from core.modules.data_contract.core.registry.mapping import DataSpec, DataSpecMap, default_map


def _catalog_entries() -> List[Tuple[DataKey, DataSpec, str]]:
    """合并 core 与 userspace 映射，保留来源标记（``system`` / ``userspace``）。"""
    custom_map = discover_userspace_map()
    entries: List[Tuple[DataKey, DataSpec, str]] = [
        (data_id, spec, "system") for data_id, spec in default_map.items()
    ]
    for data_id, spec in custom_map.items():
        if data_id in default_map:
            raise ValueError(f"发现重复 data_id 注册：{data_id.value}")
        entries.append((data_id, spec, "userspace"))
    entries.sort(key=lambda item: item[0].value)
    return entries


def _summary(data_id: DataKey, spec: DataSpec, origin: str) -> Dict[str, Any]:
    key = data_id.value
    display_name = str(spec.get("display_name") or key).strip()
    ctype = spec.get("type")
    scope = spec.get("scope")
    source = str(origin or "system").strip().lower()
    if source not in ("system", "userspace"):
        source = "system"
    return {
        "key": key,
        "display_name": display_name,
        "is_time_series": ctype == ContractType.TIME_SERIES,
        "is_per_entity": scope == ContractScope.PER_ENTITY,
        "origin": source,
        "is_custom": source == "userspace",
    }


def fetch_data_contract_catalog_page(page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    """分页返回合并后的 data contract 目录；``page`` 为 1-based，按 ``key`` 排序。"""
    ordered = _catalog_entries()
    total = len(ordered)
    if total == 0:
        return [], 0

    page = max(1, int(page))
    limit = max(1, int(limit))
    start = (page - 1) * limit
    chunk = ordered[start : start + limit]
    return [_summary(data_id, spec, origin) for data_id, spec, origin in chunk], total
