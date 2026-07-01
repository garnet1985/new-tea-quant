"""entity_based 单股 / batch 枚举 worker（子进程执行体）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.contracts import JobContext
from core.modules.data_contract.cache import ContractCacheManager

from core.modules.strategy.core.services.data.entity_data import EntityContractBatch, EntityDataLoader

from .compute import EntityBasedCompute

logger = logging.getLogger(__name__)


class EntityBasedWorker:
    """在子进程中执行单条枚举 job。

    流程：build_payload → EntityBasedCompute（timeline 扫描）→ 写盘。
    """

    @classmethod
    def run(cls, context: JobContext) -> Dict[str, Any]:
        payload = dict(context.payload or {})
        stock_ids = payload.get("stock_ids")
        if isinstance(stock_ids, list) and len(stock_ids) > 1:
            return cls._run_bulk(payload, stock_ids)
        stock_id = str(payload.get("stock_id") or (stock_ids or [""])[0] or "").strip()
        if not stock_id:
            return {"success": False, "error": "missing stock_id"}
        single = dict(payload)
        single["stock_id"] = stock_id
        return EntityBasedCompute(single).run()

    @classmethod
    def build_payload(
        cls,
        job: Dict[str, Any],
        global_data: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "job_id": str(job.get("job_id") or job.get("stock_id") or "enum_job"),
            "strategy_name": job["strategy_name"],
            "settings": job["settings"],
            "start_date": job["start_date"],
            "end_date": job["end_date"],
            "output_dir": job["output_dir"],
            "global_data": global_data,
            "worker_module_path": job["worker_module_path"],
            "worker_class_name": job["worker_class_name"],
            "worker_file_path": str(job.get("worker_file_path") or ""),
            "enumeration_execution_mode": job.get("enumeration_execution_mode", "entity_based"),
        }
        stock_ids = job.get("stock_ids")
        if isinstance(stock_ids, list) and stock_ids:
            payload["stock_ids"] = list(stock_ids)
            if len(stock_ids) == 1:
                payload["stock_id"] = stock_ids[0]
        else:
            payload["stock_id"] = job["stock_id"]
        return payload

    @classmethod
    def _run_bulk(cls, payload: Dict[str, Any], stock_ids: List[Any]) -> Dict[str, Any]:
        ids = [str(s).strip() for s in stock_ids if str(s).strip()]
        if not ids:
            return {"success": False, "bulk": True, "stock_results": [], "error": "empty stock_ids"}

        settings_dict = dict(payload["settings"])
        min_required = EntityDataLoader.min_required_records(settings_dict)
        actual_start = EntityDataLoader.enumeration_actual_start_date(
            str(payload["start_date"]),
            min_required,
        )

        shared_cache = ContractCacheManager()
        job_batch = EntityContractBatch.hydrate(
            entity_ids=ids,
            settings=settings_dict,
            start=actual_start,
            end=str(payload["end_date"]),
            contract_cache=shared_cache,
            global_data=payload.get("global_data") or {},
            fresh_strategy_cache=True,
        )

        stock_results: List[Dict[str, Any]] = []
        for stock_id in ids:
            sub_payload = dict(payload)
            sub_payload["stock_id"] = stock_id
            sub_payload.pop("stock_ids", None)
            try:
                stock_results.append(
                    EntityBasedCompute(
                        sub_payload,
                        contract_cache=shared_cache,
                        job_batch=job_batch,
                    ).run()
                )
            except Exception as exc:
                logger.error("enumeration failed: stock_id=%s error=%s", stock_id, exc, exc_info=True)
                stock_results.append(
                    {
                        "success": False,
                        "stock_id": stock_id,
                        "opportunities": [],
                        "error": str(exc),
                    }
                )

        return {
            "success": all(bool(row.get("success")) for row in stock_results),
            "bulk": True,
            "stock_results": stock_results,
            "stock_ids": ids,
        }


__all__ = ["EntityBasedWorker"]
