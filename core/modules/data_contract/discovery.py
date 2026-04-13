from __future__ import annotations

import importlib
from typing import Any, Mapping, cast

from core.infra.project_context import ProjectContextManager
from core.modules.data_contract.contract_const import DataKey
from core.modules.data_contract.mapping import DataSpec, DataSpecMap


def discover_userspace_map() -> DataSpecMap:
    """
    Discover userspace map from `userspace.data_contract.mapping`.

    Uses `PathManager.data_contract()` to decide whether userspace package should exist.
    Supported variable names in userspace mapping module:
    - `custom_map` (preferred)
    - `default_map`
    - `DATA_CONTRACT_MAP`
    """
    ctx = ProjectContextManager()
    userspace_dc_dir = ctx.path.data_contract()
    if not userspace_dc_dir.exists():
        return {}

    mapping_file = ctx.path.data_contract_mapping()
    if not mapping_file.exists():
        return {}

    module_name = "userspace.data_contract.mapping"
    try:
        mod = importlib.import_module(module_name)
    except ImportError:
        return {}

    raw_map = (
        getattr(mod, "custom_map", None)
        or getattr(mod, "default_map", None)
        or getattr(mod, "DATA_CONTRACT_MAP", None)
    )
    if raw_map is None:
        return {}
    if not isinstance(raw_map, Mapping):
        raise TypeError(f"{module_name} 中的映射必须是 Mapping 类型，当前为 {type(raw_map)!r}")

    normalized: DataSpecMap = {}
    for raw_key, raw_spec in raw_map.items():
        data_key = _normalize_key(raw_key)
        if not isinstance(raw_spec, Mapping):
            raise TypeError(
                f"{module_name} 中 data_id={data_key.value} 的 spec 必须是 Mapping 类型，当前为 {type(raw_spec)!r}"
            )
        normalized[data_key] = cast(DataSpec, dict(raw_spec))
    return normalized


def _normalize_key(key: Any) -> DataKey:
    if isinstance(key, DataKey):
        return key
    if isinstance(key, str):
        return DataKey(key)
    raise TypeError(f"userspace map 的 key 必须是 DataKey 或 str，当前为 {type(key)!r}")

