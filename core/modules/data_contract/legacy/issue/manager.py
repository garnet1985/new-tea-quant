from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional, Sequence

from core.modules.data_contract.core.cache import (
    ContractCacheManager,
    ContractCacheScope,
    resolve_cache_scope,
)
from core.modules.data_contract.core.contract.data_class.contract_info import ContractInfo
from core.modules.data_contract.core.contract.data_class.issue_result import IssueResult
from core.modules.data_contract.core.contract.contracts import DataContract
from core.modules.data_contract.core.issue.cache_guard import reject_per_entity_cache_overrides
from core.modules.data_contract.core.issue.issuer import ContractIssuer
from core.modules.data_contract.core.registry.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.core.registry.discovery import discover_userspace_map
from core.modules.data_contract.core.registry.mapping import DataSpec, DataSpecMap, default_map

_NON_TS_LOAD_WINDOW = "__static__"
_TS_FULL_RANGE_WINDOW = "__full__"


class DataContractManager:
    """内部：mapping 合并、签发、加载、GLOBAL cache。"""

    def __init__(
        self,
        *,
        contract_cache: ContractCacheManager,
        cache_enabled: bool = True,
    ) -> None:
        custom_map = self._discover_custom_map()
        self.map: DataSpecMap = self._merge_map(default_map, custom_map)
        self.issuer = ContractIssuer(self.map)
        self._contract_cache = contract_cache
        self._cache_enabled = cache_enabled

    def info(self, data_key: DataKey) -> ContractInfo:
        spec = self.map.get(data_key)
        if not spec:
            raise ValueError(f"未找到 data_id：{data_key.value}")
        scope = spec.get("scope")
        ctype = spec.get("type")
        if scope is None or ctype is None:
            raise ValueError(f"data_id={data_key.value} mapping 不完整")
        cache_scope = resolve_cache_scope(spec)
        has_cache = (
            self._cache_enabled
            and scope == ContractScope.GLOBAL
            and cache_scope != ContractCacheScope.NONE
        )
        loader_cls = spec.get("loader")
        loader_name = loader_cls.__name__ if isinstance(loader_cls, type) else str(loader_cls)
        time_axis_field = spec.get("time_axis_field")
        time_axis_format = spec.get("time_axis_format")
        supports_start_end = ctype == ContractType.TIME_SERIES
        return ContractInfo(
            data_key=data_key,
            scope=scope,
            contract_type=ctype,
            display_name=str(spec.get("display_name", data_key.value)),
            loader_name=loader_name,
            defaults=dict(spec.get("defaults", {})),
            unique_keys=list(spec.get("unique_keys", [])),
            has_cache=has_cache,
            time_axis_field=time_axis_field,
            time_axis_format=time_axis_format,
            supports_start_end=supports_start_end,
            cache_scope=cache_scope,
        )

    def issue(
        self,
        data_id: DataKey,
        *,
        entity_id: Optional[str] = None,
        entity_ids: Optional[Sequence[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        should_load_initially: bool = True,
        data: Any = None,
        data_by_entity: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
        **override_params: Any,
    ) -> IssueResult:
        if data is not None and data_by_entity is not None:
            raise ValueError("data 与 data_by_entity 互斥，不可同时传入")

        preloaded = data is not None or data_by_entity is not None
        if preloaded:
            should_load_initially = False

        spec = self.map.get(data_id)
        if not spec:
            raise ValueError(f"未找到 data_id：{data_id.value}")

        reject_per_entity_cache_overrides(data_id, spec.get("scope"), override_params)

        normalized_entity_ids = self._normalize_entity_ids(entity_id, entity_ids)
        self._validate_issue_args(spec, normalized_entity_ids, start, end)
        eff_start, eff_end = self._effective_load_window(spec, start, end)
        scope = spec.get("scope")

        issue_params = dict(override_params)
        if start is not None and end is not None:
            issue_params["start"] = start
            issue_params["end"] = end

        if scope == ContractScope.GLOBAL:
            contract = self.issuer.issue(data_id, entity_id=None, **issue_params)
            result = IssueResult(
                data_id=data_id,
                scope=ContractScope.GLOBAL,
                contract=contract,
                request_start=start,
                request_end=end,
                load_window_start=eff_start,
                load_window_end=eff_end,
            )
        else:
            assert normalized_entity_ids is not None
            by_entity = {
                eid: self.issuer.issue(data_id, entity_id=eid, **issue_params)
                for eid in normalized_entity_ids
            }
            result = IssueResult(
                data_id=data_id,
                scope=ContractScope.PER_ENTITY,
                by_entity=by_entity,
                request_start=start,
                request_end=end,
                load_window_start=eff_start,
                load_window_end=eff_end,
                entity_ids=tuple(normalized_entity_ids),
            )

        if should_load_initially:
            self.load(result)
        elif preloaded:
            self._bind_preloaded_data(result, data=data, data_by_entity=data_by_entity)
        return result

    def _bind_preloaded_data(
        self,
        result: IssueResult,
        *,
        data: Any,
        data_by_entity: Optional[Mapping[str, Sequence[Mapping[str, Any]]]],
    ) -> None:
        if result.contract is not None:
            if data is None:
                raise ValueError("GLOBAL issue 绑定预加载 data 时须传 data")
            result.contract.data = list(data)
            return

        if result.by_entity is None:
            raise ValueError(f"空的 IssueResult：data_id={result.data_id.value}")

        if data_by_entity is not None:
            for eid, contract in result.by_entity.items():
                rows = data_by_entity.get(eid)
                if rows is None:
                    raise ValueError(f"data_by_entity 缺少 entity_id={eid!r}")
                contract.data = list(rows)
            return

        if data is not None:
            if len(result.by_entity) != 1:
                raise ValueError("PER_ENTITY 多 entity issue 须传 data_by_entity，不可仅传 data")
            eid = next(iter(result.by_entity))
            result.by_entity[eid].data = list(data)
            return

        raise ValueError("预加载 issue 须传 data（GLOBAL/单 entity）或 data_by_entity（PER_ENTITY）")

    def load(self, issued: IssueResult) -> IssueResult:
        spec = self.map.get(issued.data_id)
        if spec is None:
            raise ValueError(f"未找到 data_id：{issued.data_id.value}")

        eff_start = issued.load_window_start or _NON_TS_LOAD_WINDOW
        eff_end = issued.load_window_end or _NON_TS_LOAD_WINDOW

        if issued.contract is not None:
            self._load_global_contract(issued.contract, spec, eff_start, eff_end)
        elif issued.by_entity is not None:
            entity_ids = list(issued.entity_ids or tuple(issued.by_entity.keys()))
            self._load_per_entity(dict(issued.by_entity), spec, entity_ids, eff_start, eff_end)
        else:
            raise ValueError(f"空的 IssueResult：data_id={issued.data_id.value}")

        return issued

    def _load_global_contract(
        self,
        contract: DataContract,
        spec: DataSpec,
        eff_start: str,
        eff_end: str,
    ) -> None:
        cache_scope = resolve_cache_scope(spec)
        if not self._cache_enabled or cache_scope == ContractCacheScope.NONE:
            contract.load(start=eff_start, end=eff_end)
            return

        data_id = contract.meta.data_id
        key = self._materialize_cache_key(
            data_id,
            eff_start,
            eff_end,
            None,
            contract.loader_params,
        )
        entry = self._contract_cache.get(cache_scope, key)
        if entry is not None and entry.data is not None:
            contract.data = self._clone_cached_payload(entry.data)
            return

        contract.load(start=eff_start, end=eff_end)
        to_store = self._clone_cached_payload(contract.data)
        self._contract_cache.put_for_scope(cache_scope, key, meta={}, data=to_store)
        contract.data = self._clone_cached_payload(to_store)

    def _load_per_entity(
        self,
        by_entity: dict[str, DataContract],
        spec: DataSpec,
        entity_ids: Sequence[str],
        eff_start: str,
        eff_end: str,
    ) -> None:
        sample = next(iter(by_entity.values()))
        loader = sample.loader
        if loader is None:
            raise RuntimeError(f"data_id={sample.meta.data_id.value} 未绑定 loader，无法 load")

        load_params = self._loader_params_for_window(
            dict(sample.loader_params),
            spec,
            eff_start,
            eff_end,
        )
        raw_by_entity = loader.load_batch(entity_ids, load_params, context=None)
        for eid, contract in by_entity.items():
            contract.data = self._clone_cached_payload(raw_by_entity.get(eid))

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
    def _loader_params_for_window(
        loader_params: dict[str, Any],
        spec: DataSpec,
        eff_start: str,
        eff_end: str,
    ) -> dict[str, Any]:
        params = dict(loader_params)
        if spec.get("type") == ContractType.NON_TIME_SERIES:
            return params
        if eff_start == _TS_FULL_RANGE_WINDOW:
            return params
        params["start"] = eff_start
        params["end"] = eff_end
        return params

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
