from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional, Sequence

from core.modules.data_contract.cache import (
    ContractCacheManager,
    ContractCacheScope,
    resolve_cache_scope,
)
from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.contract_issuer import ContractIssuer
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.data_class.issue_result import IssueResult
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
        entity_ids: Optional[Sequence[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **override_params: Any,
    ) -> IssueResult:
        """
        签发 ``IssueResult``。可缓存的 GLOBAL 在命中策略下 **直接物化并写入 ``contract.data``**；
        ``PER_ENTITY`` 返回 ``by_entity``；在具备明确 load 窗口时会通过 loader 物化各 entity 的 ``data``。

        参数约定见 ``docs/DECISIONS.md``。
        """
        spec = self.map.get(data_id)
        if not spec:
            raise ValueError(f"未找到 data_id：{data_id.value}")

        normalized_entity_ids = self._normalize_entity_ids(entity_id, entity_ids)
        self._validate_issue_args(spec, normalized_entity_ids, start, end)
        eff_start, eff_end = self._effective_load_window(spec, start, end)
        scope = spec.get("scope")

        if scope == ContractScope.GLOBAL:
            contract = self._issue_global(
                data_id,
                spec,
                eff_start,
                eff_end,
                entity_id=None,
                override_params=override_params,
            )
            return IssueResult(
                data_id=data_id,
                scope=ContractScope.GLOBAL,
                contract=contract,
            )

        assert normalized_entity_ids is not None
        by_entity = self._issue_per_entity(
            data_id,
            spec,
            normalized_entity_ids,
            eff_start,
            eff_end,
            override_params=override_params,
        )
        return IssueResult(
            data_id=data_id,
            scope=ContractScope.PER_ENTITY,
            by_entity=by_entity,
        )

    def _issue_global(
        self,
        data_id: DataKey,
        spec: DataSpec,
        eff_start: str,
        eff_end: str,
        *,
        entity_id: Optional[str],
        override_params: Mapping[str, Any],
    ) -> DataContract:
        cache_scope = resolve_cache_scope(spec)
        eff_entity_id = None

        if cache_scope == ContractCacheScope.NONE:
            return self.issuer.issue(data_id, entity_id=eff_entity_id, **override_params)

        key = self._materialize_cache_key(
            data_id, eff_start, eff_end, eff_entity_id, override_params
        )
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

    def _issue_per_entity(
        self,
        data_id: DataKey,
        spec: DataSpec,
        entity_ids: Sequence[str],
        eff_start: str,
        eff_end: str,
        *,
        override_params: Mapping[str, Any],
    ) -> dict[str, DataContract]:
        contracts: dict[str, DataContract] = {}
        for eid in entity_ids:
            contracts[eid] = self.issuer.issue(data_id, entity_id=eid, **override_params)

        if not self._should_materialize_per_entity(spec, eff_start, eff_end):
            return contracts

        sample = next(iter(contracts.values()))
        loader = sample.loader
        if loader is None:
            return contracts

        load_params = self._loader_params_for_window(
            dict(sample.loader_params),
            spec,
            eff_start,
            eff_end,
        )
        raw_by_entity = loader.load_batch(entity_ids, load_params, context=None)

        for eid, contract in contracts.items():
            payload = raw_by_entity.get(eid)
            contract.data = self._clone_cached_payload(payload)

        return contracts

    @staticmethod
    def _normalize_entity_ids(
        entity_id: Optional[str],
        entity_ids: Optional[Sequence[str]],
    ) -> Optional[list[str]]:
        if entity_id is not None and entity_ids is not None:
            raise ValueError("entity_id 与 entity_ids 互斥，不可同时传入")
        if entity_ids is not None:
            ids = [str(x).strip() for x in entity_ids if str(x).strip()]
            if not ids:
                raise ValueError("PER_ENTITY 的 data_id 须提供非空 entity_ids")
            return ids
        if entity_id is not None and str(entity_id).strip():
            return [str(entity_id).strip()]
        return None

    @staticmethod
    def _should_materialize_per_entity(
        spec: DataSpec,
        eff_start: str,
        eff_end: str,
    ) -> bool:
        if spec.get("type") == ContractType.NON_TIME_SERIES:
            return True
        return eff_start != _TS_FULL_RANGE_WINDOW and eff_end != _TS_FULL_RANGE_WINDOW

    @staticmethod
    def _loader_params_for_window(
        loader_params: dict[str, Any],
        spec: DataSpec,
        eff_start: str,
        eff_end: str,
    ) -> dict[str, Any]:
        if spec.get("type") == ContractType.NON_TIME_SERIES:
            return loader_params
        if eff_start == _TS_FULL_RANGE_WINDOW:
            return loader_params
        loader_params["start"] = eff_start
        loader_params["end"] = eff_end
        return loader_params

    def _validate_issue_args(
        self,
        spec: DataSpec,
        entity_ids: Optional[Sequence[str]],
        start: Optional[str],
        end: Optional[str],
    ) -> None:
        if spec.get("scope") == ContractScope.PER_ENTITY:
            if not entity_ids:
                raise ValueError("PER_ENTITY 的 data_id 须提供非空 entity_id 或 entity_ids")
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
