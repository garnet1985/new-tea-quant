#!/usr/bin/env python3
"""Job Builder Helper - 作业构建助手。"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Tuple

from core.modules.strategy.enums import ExecutionMode

logger = logging.getLogger(__name__)


def _strategy_job_fields(strategy_info: Any) -> Tuple[str, Any, str, str]:
    if isinstance(strategy_info, dict):
        return (
            strategy_info["name"],
            strategy_info["settings"],
            strategy_info["worker_module_path"],
            strategy_info["worker_class_name"],
        )
    return (
        strategy_info.name,
        strategy_info.settings,
        strategy_info.worker_module_path,
        strategy_info.worker_class_name,
    )


class JobBuilderHelper:
    @staticmethod
    def build_scan_jobs(
        stock_list: List[str],
        strategy_info: Dict[str, Any],
        date: str,
    ) -> List[Dict[str, Any]]:
        jobs = []
        name, settings, worker_module_path, worker_class_name = _strategy_job_fields(
            strategy_info
        )
        for stock_id in stock_list:
            jobs.append(
                {
                    "stock_id": stock_id,
                    "execution_mode": ExecutionMode.SCAN.value,
                    "strategy_name": name,
                    "settings": settings.to_dict(),
                    "scan_date": date,
                    "worker_module_path": worker_module_path,
                    "worker_class_name": worker_class_name,
                }
            )
        return jobs

    @staticmethod
    def build_simulate_jobs(
        stock_list: List[str],
        strategy_info: Dict[str, Any],
        session_id: str,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        jobs = []
        name, settings, worker_module_path, worker_class_name = _strategy_job_fields(
            strategy_info
        )
        for stock_id in stock_list:
            jobs.append(
                {
                    "stock_id": stock_id,
                    "execution_mode": ExecutionMode.SIMULATE.value,
                    "strategy_name": name,
                    "settings": settings.to_dict(),
                    "session_id": session_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "worker_module_path": worker_module_path,
                    "worker_class_name": worker_class_name,
                }
            )
        return jobs

