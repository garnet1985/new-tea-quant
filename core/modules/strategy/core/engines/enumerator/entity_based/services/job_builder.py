"""Job构建工具类（无状态）。"""
from __future__ import annotations

from typing import List, Dict, Any

from core.modules.backtest_engine.contracts import BacktestJob
from .runtime_context.context import EntityBasedRuntimeContext


class JobBuilder:
    """Job构建工具类（无状态，每次调用传入足够参数）。"""

    @staticmethod
    def build_jobs(context: EntityBasedRuntimeContext) -> List[BacktestJob]:
        """构建jobs（传入context，无memory）。"""

        jobs: List[BacktestJob] = []

        for entity_id in context.info.entity_ids:
            job = BacktestJob(
                id=entity_id,
                payload={
                    # ── 子进程需要的字段（Payload传递）──
                    "entity_id": entity_id,
                    "strategy_id": context.info.strategy_id,
                    "key": context.info.key,
                    "start_date": context.info.start_date,
                    "end_date": context.info.end_date,
                    "hooks_module_path": context.strategy_info.hooks_module_path,
                    "hooks_class_name": context.strategy_info.hooks_class.__name__,
                    "settings_dict": context.settings.to_dict(),  # 传递settings dict

                    # ── 共享内存字段（TODO）──
                    # "shm_name": shm_name,
                    # "shm_size": shm_size,
                }
            )
            jobs.append(job)

        return jobs


__all__ = ["JobBuilder"]