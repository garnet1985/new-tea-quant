"""entity_based job 构建。"""
from __future__ import annotations

from typing import Any, Dict, List


class EntityBasedJobs:
    """为 BacktestEngine entity_based 模式组装 strategy 侧 jobs。"""

    EXECUTION_MODE = "entity_based"

    @classmethod
    def build(
        cls,
        *,
        strategy_name: str,
        settings_payload: Dict[str, Any],
        output_dir: str,
        worker_ref: Dict[str, str],
        stock_ids: List[str],
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        for raw_id in stock_ids:
            stock_id = str(raw_id).strip()
            if not stock_id:
                continue
            jobs.append(
                {
                    "entity_id": stock_id,
                    "stock_id": stock_id,
                    "job_id": stock_id,
                    "strategy_name": strategy_name,
                    "settings": settings_payload,
                    "start_date": start_date,
                    "end_date": end_date,
                    "output_dir": output_dir,
                    "worker_module_path": worker_ref["worker_module_path"],
                    "worker_class_name": worker_ref["worker_class_name"],
                    "worker_file_path": str(worker_ref.get("worker_file_path") or ""),
                    "enumeration_execution_mode": cls.EXECUTION_MODE,
                }
            )
        return jobs


__all__ = ["EntityBasedJobs"]
