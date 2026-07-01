"""entity_based job init：子进程内批量装载数据 + 建 cursor（execute 之前）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

from core.modules.backtest_engine.contracts import JobContext
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.strategy.core.engines.enumerator.entity_based.execute_payload import (
    EntityBasedExecutePayload,
)
from core.modules.strategy.core.services.data.entity_data import (
    EntityContractBatch,
    EntityDataLoader,
)
from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig


@dataclass
class EntityBasedJobSession:
    """一次 BacktestEngine job 的数据会话：批量装载后的 loader + cursor。"""

    entity_ids: List[str]
    settings: Dict[str, Any]
    global_data: Dict[str, Any]
    actual_start: str
    end_date: str
    contract_cache: ContractCacheManager
    contract_batch: EntityContractBatch
    _loaders: Dict[str, EntityDataLoader] = field(default_factory=dict)

    def loader_for(self, entity_id: str) -> EntityDataLoader:
        eid = str(entity_id).strip()
        loader = self._loaders.get(eid)
        if loader is None:
            raise ValueError(f"entity_id {eid!r} 不在当前 job 批量装载范围内")
        return loader

    def release(self) -> None:
        for loader in self._loaders.values():
            loader.clear_working_state()
        self._loaders.clear()


class EntityBasedJobInit:
    """BacktestEngine job 进入 execute 前的 init 阶段。

    职责（通俗说法）：
    - **批量装载**：把本 job bundled 的全部 entity 数据一次性从 DB 读入内存
      （底层 ``loader.load_batch``，不是清洗/润色数据）。
    - **建 cursor**：每个 entity 挂到 DataCursor，后续只按 as_of 截取可见前缀。
    """

    @classmethod
    def initialize(cls, raw: Mapping[str, Any]) -> EntityBasedJobSession:
        payload = EntityBasedExecutePayload.from_mapping(raw)
        entity_ids = cls._resolve_entity_ids(payload, raw)
        settings = dict(payload.settings)
        min_required = StrategyDataConfig(settings).min_required_records
        actual_start = EntityDataLoader.enumeration_actual_start_date(
            payload.start_date,
            min_required,
        )

        contract_cache = ContractCacheManager()
        contract_batch = EntityContractBatch.batch_load(
            entity_ids=entity_ids,
            settings=settings,
            start=actual_start,
            end=payload.end_date,
            contract_cache=contract_cache,
            global_data=payload.global_data,
            fresh_strategy_cache=True,
        )

        loaders: Dict[str, EntityDataLoader] = {}
        for entity_id in entity_ids:
            loader = EntityDataLoader(
                stock_id=entity_id,
                settings=settings,
                global_data=payload.global_data,
                contract_cache=contract_cache,
            )
            loader.attach_from_batch(
                contract_batch,
                start_date=actual_start,
                end_date=payload.end_date,
            )
            loaders[entity_id] = loader

        return EntityBasedJobSession(
            entity_ids=list(entity_ids),
            settings=settings,
            global_data=dict(payload.global_data),
            actual_start=actual_start,
            end_date=payload.end_date,
            contract_cache=contract_cache,
            contract_batch=contract_batch,
            _loaders=loaders,
        )

    @staticmethod
    def _resolve_entity_ids(
        payload: EntityBasedExecutePayload,
        raw: Mapping[str, Any],
    ) -> List[str]:
        bundled = raw.get("entity_ids")
        if isinstance(bundled, list) and bundled:
            ids = [str(x).strip() for x in bundled if str(x).strip()]
            if not ids:
                raise ValueError("entity_based job.entity_ids 无有效条目")
            return ids
        return [payload.entity_id]

    @classmethod
    def on_job_context(cls, context: JobContext) -> EntityBasedJobSession:
        """BacktestEngine RunCallbacks.on_job_init 入口。"""
        from core.modules.strategy.core.engines.enumerator.entity_based.worker import (
            EntityBasedWorker,
        )

        payload = EntityBasedWorker.build_payload(dict(context.payload))
        return cls.initialize(payload)

    @staticmethod
    def release_job_context(context: JobContext) -> None:
        """BacktestEngine RunCallbacks.on_job_release 入口。"""
        session = context.init
        if isinstance(session, EntityBasedJobSession):
            session.release()
            context.init = None


__all__ = ["EntityBasedJobInit", "EntityBasedJobSession"]
