"""entity_based 子进程逻辑 — BacktestEngine 三阶段回调。

读子进程从这里开始::

    EntityBasedWorker.on_init      ← RunCallbacks.on_job_init
    EntityBasedWorker.execute      ← execute_fn
    EntityBasedWorker.on_release   ← RunCallbacks.on_job_release

单股 scan 见 ``executor.py``；主进程见 ``pipeline.py``。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional

from core.modules.backtest_engine.contracts import BacktestJob, JobContext

from core.modules.strategy.core.engines.enumerator.entity_based.execute_payload import (
    EntityBasedExecutePayload,
)
from core.modules.strategy.core.engines.enumerator.entity_based.execute_result import (
    EntityBasedExecuteResult,
)
from core.modules.strategy.core.engines.enumerator.entity_based.job_session import (
    EntityBasedJobSession,
)
from core.modules.strategy.core.services.data.entity_data import (
    EntityContractBatch,
    EntityDataLoader,
)
from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig

logger = logging.getLogger(__name__)


class EntityBasedWorker:
    """子进程 job 生命周期：init（装载）→ execute（scan）→ release。"""

    @classmethod
    def on_init(cls, context: JobContext) -> EntityBasedJobSession:
        worker_payload = cls.build_worker_payload(cls.normalize_engine_payload(context.payload))
        return cls._load_session(worker_payload)

    @classmethod
    def execute(cls, context: JobContext) -> Dict[str, Any]:
        session = cls._require_session(context)
        job = cls.normalize_engine_payload(context.payload)

        batch_entities = job.get("jobs")
        if isinstance(batch_entities, list) and batch_entities:
            dispatch_job = cls.merge_batch_payload(batch_entities, context.job_id)
            worker_payload = cls.build_worker_payload(dispatch_job)
        else:
            worker_payload = cls.build_worker_payload(job)

        entity_ids = list(session.entity_ids)
        if len(entity_ids) > 1:
            return cls._execute_entities(worker_payload, session, entity_ids)

        from .executor import EntityBasedExecutor

        return EntityBasedExecutor.from_mapping(worker_payload, session=session).execute()

    @classmethod
    def on_release(cls, context: JobContext) -> None:
        session = context.init
        if isinstance(session, EntityBasedJobSession):
            session.release()
            context.init = None

    @staticmethod
    def normalize_engine_payload(raw: Mapping[str, Any]) -> Dict[str, Any]:
        job = dict(raw)
        if "global_data" not in job:
            global_data = job.pop("_global_data", None)
            if isinstance(global_data, dict):
                job["global_data"] = global_data
        return job

    @classmethod
    def build_worker_payload(
        cls,
        job: Dict[str, Any],
        global_data: Optional[Dict[str, List[Any]]] = None,
    ) -> Dict[str, Any]:
        if global_data is not None:
            job = {**job, "global_data": global_data}

        if "entity_id" not in job:
            raise ValueError("entity_based job 缺少 entity_id")

        entity_id = str(job["entity_id"]).strip()
        if not entity_id:
            raise ValueError("entity_based job.entity_id 不能为空")

        global_data_dict = job.get("global_data")
        if not isinstance(global_data_dict, dict):
            raise ValueError("entity_based job.global_data 须为 dict")

        payload: Dict[str, Any] = {
            "job_id": str(job.get("job_id") or entity_id),
            "entity_id": entity_id,
            "strategy_name": job["strategy_name"],
            "settings": job["settings"],
            "start_date": job["start_date"],
            "end_date": job["end_date"],
            "output_dir": job["output_dir"],
            "global_data": global_data_dict,
            "open_dates": list(job["open_dates"]),
            "backtest_calendar": dict(job["backtest_calendar"]),
            "worker_module_path": job["worker_module_path"],
            "worker_class_name": job["worker_class_name"],
            "worker_file_path": str(job.get("worker_file_path") or ""),
            "enumeration_execution_mode": job["enumeration_execution_mode"],
        }

        entity_ids = job.get("entity_ids")
        if isinstance(entity_ids, list) and entity_ids:
            payload["entity_ids"] = [
                str(x).strip() for x in entity_ids if str(x).strip()
            ]

        for key, value in job.items():
            if str(key).startswith("_"):
                payload[key] = value
        return payload

    @staticmethod
    def merge_batch_payload(entities: List[Dict[str, Any]], batch_job_id: str) -> Dict[str, Any]:
        rows = BacktestJob.batch_payloads(entities)
        base = dict(rows[0])
        entity_ids = [
            str(row.get("entity_id") or "").strip()
            for row in rows
            if str(row.get("entity_id") or "").strip()
        ]
        if not entity_ids:
            raise ValueError("entity_based batch payload 缺少 entity_id")

        merged = {
            key: value
            for key, value in base.items()
            if key not in {"job_id", "entity_id", "entity_ids", "id", "payload"}
        }
        merged["job_id"] = entity_ids[0] if len(entity_ids) == 1 else batch_job_id
        merged["entity_ids"] = entity_ids
        if len(entity_ids) == 1:
            merged["entity_id"] = entity_ids[0]
        global_data = base.get("_global_data")
        if isinstance(global_data, dict):
            merged["global_data"] = global_data
        return merged

    @classmethod
    def _load_session(cls, worker_payload: Dict[str, Any]) -> EntityBasedJobSession:
        payload = EntityBasedExecutePayload.from_mapping(worker_payload)
        entity_ids = cls._resolve_entity_ids(payload, worker_payload)
        settings = dict(payload.settings)
        min_required = StrategyDataConfig(settings).min_required_records
        actual_start = EntityDataLoader.enumeration_actual_start_date(
            payload.start_date,
            min_required,
        )

        contract_batch = EntityContractBatch.batch_load(
            entity_ids=entity_ids,
            settings=settings,
            start=actual_start,
            end=payload.end_date,
            global_data=payload.global_data,
            fresh_strategy_cache=True,
        )

        loaders: Dict[str, EntityDataLoader] = {}
        for entity_id in entity_ids:
            loader = EntityDataLoader(
                stock_id=entity_id,
                settings=settings,
                global_data=payload.global_data,
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
            contract_batch=contract_batch,
            _loaders=loaders,
        )

    @classmethod
    def _execute_entities(
        cls,
        worker_payload: Dict[str, Any],
        session: EntityBasedJobSession,
        entity_ids: List[str],
    ) -> Dict[str, Any]:
        from .executor import EntityBasedExecutor

        entity_results: List[Dict[str, Any]] = []
        for entity_id in entity_ids:
            sub_payload = {**worker_payload, "entity_id": entity_id}
            try:
                entity_results.append(
                    EntityBasedExecutor.from_mapping(sub_payload, session=session).execute()
                )
            except Exception as exc:
                logger.error(
                    "enumeration failed: entity_id=%s error=%s",
                    entity_id,
                    exc,
                    exc_info=True,
                )
                entity_results.append(
                    EntityBasedExecuteResult.failed(
                        entity_id=entity_id,
                        error=str(exc),
                    ).to_dict()
                )

        return {
            "success": all(bool(row.get("success")) for row in entity_results),
            "bulk": True,
            "stock_results": entity_results,
            "entity_results": entity_results,
            "stock_ids": entity_ids,
            "entity_ids": entity_ids,
        }

    @classmethod
    def _require_session(cls, context: JobContext) -> EntityBasedJobSession:
        session = context.init
        if not isinstance(session, EntityBasedJobSession):
            raise ValueError(
                "entity_based execute 要求 BacktestEngine 先执行 on_job_init"
            )
        return session

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


__all__ = ["EntityBasedWorker"]
