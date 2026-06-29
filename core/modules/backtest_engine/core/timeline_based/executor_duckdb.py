"""
Backtest Engine - Timeline-based Executor (DuckDB Branch)

时间线模式的执行器（DuckDB特殊处理）。

职责：
- 继承TimelineExecutor
- 添加DuckDB scope包裹
- 处理wait_pool_children_done
- 处理prepare_main_for_worker_pool

特点：
- DuckDB特殊处理（释放主进程锁，子进程读库）
- 继承TimelineExecutor核心逻辑
- 保持代码简洁，不污染主逻辑
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.timeline_based.executor import (
    TimelineExecutor,
    ExecutionResult,
    OnResultHook,
    OnReleaseHook,
)
from core.modules.backtest_engine.core.timeline_based.planner import (
    DispatchPlan,
    JobBatch,
)
from core.modules.backtest_engine.core.shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class TimelineExecutorDuckDB(TimelineExecutor):
    """时间线模式执行器（DuckDB特殊处理）。
    
    继承TimelineExecutor，添加DuckDB scope包裹。
    """
    
    @staticmethod
    def execute(
        plan: DispatchPlan,
        batches: List[JobBatch],
        context: ExecutionContext,
        on_result: Optional[OnResultHook] = None,
        on_release: Optional[OnReleaseHook] = None,
        log_label: str = "执行",
        data_mgr: Optional[Any] = None,
    ) -> ExecutionResult:
        """接受plan并执行jobs（DuckDB特殊处理）。
        
        Args:
            plan: 调度规划
            batches: 切割后的job批次
            context: 执行上下文
            on_result: 结果回调
            on_release: 释放回调
            log_label: 日志标签
            data_mgr: DataManager实例（可选）
            
        Returns:
            ExecutionResult: 执行结果
        """
        from core.infra.db.engines.duckdb.process_pool_scope import (
            duckdb_worker_pool_main_process,
            is_duckdb_backend,
            resolve_data_manager,
        )
        
        # 检查是否为DuckDB后端
        if not is_duckdb_backend(data_mgr):
            logger.info("%s非DuckDB后端，使用标准executor", log_label)
            return TimelineExecutor.execute(
                plan, batches, context, on_result, on_release, log_label
            )
        
        # DuckDB特殊处理：包裹scope
        logger.info("%sDuckDB后端，使用DuckDB executor", log_label)
        
        # 解析DataManager
        dm = resolve_data_manager(data_mgr, allow_create=True)
        
        # 包裹DuckDB scope（释放主进程锁，子进程读库）
        with duckdb_worker_pool_main_process(dm):
            return TimelineExecutor.execute(
                plan, batches, context, on_result, on_release, log_label
            )


__all__ = ["TimelineExecutorDuckDB"]