#!/usr/bin/env python3
"""Cross-engine job builder helpers."""

from typing import Any, Dict, List, Tuple

from core.modules.strategy.core.enums import ExecutionMode


def _strategy_job_fields(strategy_info: Any) -> Tuple[str, Any, str, str, str]:
    if isinstance(strategy_info, dict):
        return (
            strategy_info["name"],
            strategy_info["settings"],
            strategy_info["worker_module_path"],
            strategy_info["worker_class_name"],
            str(strategy_info.get("worker_file_path") or ""),
        )
    return (
        strategy_info.name,
        strategy_info.settings,
        strategy_info.worker_module_path,
        strategy_info.worker_class_name,
        str(strategy_info.worker_file_path),
    )


class JobBuilderHelper:
    @staticmethod
    def build_scan_jobs(
        stock_list: List[str],
        strategy_info: Dict[str, Any],
        date: str,
    ) -> List[Dict[str, Any]]:
        jobs = []
        name, settings, worker_module_path, worker_class_name, worker_file_path = (
            _strategy_job_fields(strategy_info)
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
                    "worker_file_path": worker_file_path,
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
        name, settings, worker_module_path, worker_class_name, worker_file_path = (
            _strategy_job_fields(strategy_info)
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
                    "worker_file_path": worker_file_path,
                }
            )
        return jobs


__all__ = ["JobBuilderHelper"]
