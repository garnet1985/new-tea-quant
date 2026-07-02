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
                    "entity_id": entity_id,
                    "strategy_id": context.info.strategy_id,
                    "key": context.info.key,
                    "settings": context.settings.to_dict(),
                    "start_date": context.info.start_date,
                    "end_date": context.info.end_date,
                    "output_dir": str(context.info.output_dir),
                    "version_id": context.info.version_id,
                    # TODO: 添加其他必要参数
                    # - hooks_class_ref
                    # - global_data_ref（共享内存）
                }
            )
            jobs.append(job)
        
        return jobs


__all__ = ["JobBuilder"]