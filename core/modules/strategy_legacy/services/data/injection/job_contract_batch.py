#!/usr/bin/env python3
"""
Job-scoped batch ``issue`` for enumeration / backtest dispatch.

仅加载 ``StrategySettingsView.required_data_sources``（``base_required_data`` + extras）。
股票池、日历等未声明项 **不在此 batch 内**。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.contracts import IssueResult
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.services.data.helper import normalize_declaration_item, storage_key_for


@dataclass
class StrategyJobContractBatch:
    """
    一次 dispatch job 内多 entity 的 contract 物化结果。

    PER_ENTITY 数据源经 ``issue(entity_ids=...)`` 批量加载；GLOBAL 数据源 singleton。
    """

    global_contracts: Dict[DataKey, DataContract] = field(default_factory=dict)
    per_entity_results: Dict[DataKey, IssueResult] = field(default_factory=dict)

    @classmethod
    def hydrate(
        cls,
        *,
        entity_ids: Sequence[str],
        settings: StrategySettingsView,
        start: str,
        end: str,
        global_extra_cache: Optional[Mapping[str, Sequence[Mapping[str, object]]]] = None,
        fresh_strategy_cache: bool = False,
    ) -> StrategyJobContractBatch:
        ids = [str(x).strip() for x in entity_ids if str(x).strip()]
        if not ids:
            raise ValueError("StrategyJobContractBatch.hydrate 需要非空 entity_ids")

        if fresh_strategy_cache:
            DataContracts.shared_cache().enter_strategy_run()

        dcm = DataContracts()
        batch = cls()
        st = StrategySettingsView({"data": settings.data})

        for raw in st.required_data_sources:
            item = normalize_declaration_item(st, raw)
            dk = DataKey(str(item["data_id"]))
            params = dict(item.get("params") or {})
            spec = dcm.map.get(dk)
            if spec is None:
                raise ValueError(f"未注册的 data_id：{dk.value}")

            scope = spec.get("scope")
            if scope == ContractScope.GLOBAL:
                contract = dcm.issue(
                    dk,
                    start=start,
                    end=end,
                    **params,
                ).require_contract()
                slot = storage_key_for(dk)
                if global_extra_cache is not None and slot in global_extra_cache:
                    contract.data = list(global_extra_cache[slot] or [])
                batch.global_contracts[dk] = contract
                continue

            if dk in batch.per_entity_results:
                raise ValueError(
                    f"data 声明中重复的 data_id：{dk.value!r}（dict 存储下无法同时保留两条）"
                )
            batch.per_entity_results[dk] = dcm.issue(
                dk,
                entity_ids=ids,
                start=start,
                end=end,
                **params,
            )

        return batch

    def contracts_for_entity(self, entity_id: str) -> Dict[DataKey, DataContract]:
        eid = str(entity_id).strip()
        if not eid:
            raise ValueError("contracts_for_entity 需要非空 entity_id")

        out: Dict[DataKey, DataContract] = dict(self.global_contracts)
        for dk, result in self.per_entity_results.items():
            out[dk] = result.entity(eid)
        return out

    def entity_ids(self) -> List[str]:
        for result in self.per_entity_results.values():
            if result.by_entity:
                return list(result.by_entity.keys())
        return []


__all__ = ["StrategyJobContractBatch"]
