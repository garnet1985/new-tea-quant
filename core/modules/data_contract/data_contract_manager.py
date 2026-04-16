from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional

from core.modules.data_contract.cache import (
    ContractCacheManager,
    ContractCacheScope,
    resolve_cache_scope,
)
from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.contract_issuer import ContractIssuer
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.discovery import discover_userspace_map
from core.modules.data_contract.mapping import DataSpec, DataSpecMap, default_map

# 非时序：无日期窗，用于 cache key 与 load 透传
_NON_TS_LOAD_WINDOW = "__static__"
# 时序：未传 start/end 时表示全量物化语义，用于 cache key
_TS_FULL_RANGE_WINDOW = "__full__"


class DataContractManager:
    """Manager: discover/merge map；对外以 ``issue`` 为统一入口（含可缓存 GLOBAL 的物化）。详见 ``docs/DECISIONS.md``。"""

    def __init__(self, *, contract_cache: ContractCacheManager) -> None:
        custom_map = self._discover_custom_map()
        self.map: DataSpecMap = self._merge_map(default_map, custom_map)
        self.issuer = ContractIssuer(self.map)
        self._contract_cache = contract_cache

    def issue(
        self,
        data_id: DataKey,
        *,
        entity_id: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **override_params: Any,
    ) -> DataContract:
        """
        签发 ``DataContract``。可缓存的 GLOBAL 数据在命中策略下 **直接物化并写入 ``contract.data``**；
        ``PER_ENTITY`` 等不缓存项仅装配句柄，``data`` 为空，需再 ``load``。

        参数约定见 ``docs/DECISIONS.md``。
        """
        spec = self.map.get(data_id)
        if not spec:
            raise ValueError(f"未找到 data_id：{data_id.value}")

        self._validate_issue_args(spec, entity_id, start, end)
        eff_start, eff_end = self._effective_load_window(spec, start, end)
        cache_scope = resolve_cache_scope(spec)
        # GLOBAL 不应带实体维度；忽略误传，避免 cache key 与 issuer context 被污染
        eff_entity_id = None if spec.get("scope") == ContractScope.GLOBAL else entity_id

        if cache_scope == ContractCacheScope.NONE:
            return self.issuer.issue(data_id, entity_id=eff_entity_id, **override_params)

        key = self._materialize_cache_key(data_id, eff_start, eff_end, eff_entity_id, override_params)
        entry = self._contract_cache.get(cache_scope, key)
        if entry is not None and entry.data is not None:
            contract = self.issuer.issue(data_id, entity_id=eff_entity_id, **override_params)
            contract.data = self._clone_cached_payload(entry.data)
            return contract

        contract = self.issuer.issue(data_id, entity_id=eff_entity_id, **override_params)
        data = contract.load(start=eff_start, end=eff_end)
        to_store = self._clone_cached_payload(data)
        self._contract_cache.put_for_scope(cache_scope, key, meta={}, data=to_store)
        contract.data = self._clone_cached_payload(to_store)
        return contract

    def _validate_issue_args(
        self,
        spec: DataSpec,
        entity_id: Optional[str],
        start: Optional[str],
        end: Optional[str],
    ) -> None:
        if spec.get("scope") == ContractScope.PER_ENTITY:
            if entity_id is None or not str(entity_id).strip():
                raise ValueError("PER_ENTITY 的 data_id 须提供非空 entity_id")
        if spec.get("type") == ContractType.TIME_SERIES:
            if (start is None) != (end is None):
                raise ValueError("时序数据须同时提供 start 与 end，或同时省略（省略表示全量语义）")

    def _effective_load_window(
        self,
        spec: DataSpec,
        start: Optional[str],
        end: Optional[str],
    ) -> tuple[str, str]:
        if spec.get("type") == ContractType.NON_TIME_SERIES:
            return (_NON_TS_LOAD_WINDOW, _NON_TS_LOAD_WINDOW)
        if start is None and end is None:
            return (_TS_FULL_RANGE_WINDOW, _TS_FULL_RANGE_WINDOW)
        assert start is not None and end is not None
        return (start, end)

    @staticmethod
    def _clone_cached_payload(data: Any) -> Any:
        if isinstance(data, list):
            return list(data)
        return data

    @staticmethod
    def _materialize_cache_key(
        data_id: DataKey,
        start: str,
        end: str,
        entity_id: Optional[str],
        override_params: Mapping[str, Any],
    ) -> str:
        params_obj = sorted(
            (str(k), DataContractManager._json_safe(v)) for k, v in override_params.items()
        )
        payload = {
            "data_id": data_id.value,
            "start": start,
            "end": end,
            "entity_id": entity_id,
            "params": params_obj,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"dcm:{data_id.value}:{digest}"

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (list, tuple)):
            return [DataContractManager._json_safe(v) for v in value]
        if isinstance(value, dict):
            return sorted((str(k), DataContractManager._json_safe(v)) for k, v in value.items())
        return str(value)

    def _discover_custom_map(self) -> DataSpecMap:
        return discover_userspace_map()

    def _merge_map(self, base_map: DataSpecMap, custom_map: DataSpecMap) -> DataSpecMap:
        merged: DataSpecMap = dict(base_map)
        for data_id, spec in custom_map.items():
            if data_id in merged:
                raise ValueError(f"发现重复 data_id 注册：{data_id.value}")
            merged[data_id] = spec
        return merged
