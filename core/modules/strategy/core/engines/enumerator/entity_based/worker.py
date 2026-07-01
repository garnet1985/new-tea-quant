"""entity_based 单股 / batch 枚举 worker（BacktestEngine execute_fn 入口）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.contracts import JobContext

from .execute_result import EntityBasedExecuteResult
from .executor import EntityBasedExecutor
from .job_init import EntityBasedJobSession

logger = logging.getLogger(__name__)


class EntityBasedWorker:
    """BacktestEngine execute_fn：消费 on_job_init 装载的数据，逐 entity 跑 hook。"""

    @classmethod
    def run(cls, context: JobContext) -> Dict[str, Any]:
        session = cls._require_session(context)
        payload = cls.build_payload(dict(context.payload))

        entity_ids = list(session.entity_ids)
        if len(entity_ids) > 1:
            return cls._execute_entities(payload, session, entity_ids)
        return EntityBasedExecutor.from_mapping(payload, session=session).execute()

    @classmethod
    def build_payload(
        cls,
        job: Dict[str, Any],
        global_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
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

    @classmethod
    def _require_session(cls, context: JobContext) -> EntityBasedJobSession:
        session = context.init
        if not isinstance(session, EntityBasedJobSession):
            raise ValueError(
                "entity_based execute 要求 BacktestEngine 先执行 RunCallbacks.on_job_init"
            )
        return session

    @classmethod
    def _execute_entities(
        cls,
        payload: Dict[str, Any],
        session: EntityBasedJobSession,
        entity_ids: List[str],
    ) -> Dict[str, Any]:
        entity_results: List[Dict[str, Any]] = []
        for entity_id in entity_ids:
            sub_payload = {**payload, "entity_id": entity_id}
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


__all__ = ["EntityBasedWorker"]
