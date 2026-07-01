"""entity_based 模式 runtime context（Layer 3 特化）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.performance import (
    EntityBasedPerformance,
    resolve_entity_based_performance,
)

from core.modules.strategy.core.context.backtest_runtime import BacktestRuntimeContext
from core.modules.strategy.core.context.strategy_context import StrategyContext


@dataclass
class EntityBasedRuntimeContext(BacktestRuntimeContext):
    """entity_based 回测 runtime。"""

    EXECUTION_MODE: ClassVar[BacktestMode] = BacktestMode.ENTITY_BASED

    RESERVE_CORES: ClassVar[int] = 2
    MAX_PARALLEL_JOBS_CAP: ClassVar[Optional[int]] = None
    MEMORY_BUDGET_MB: ClassVar[str] = "auto"
    MEMORY_FLOOR_MB: ClassVar[str] = "auto"
    ENTITIES_PER_JOB: ClassVar[str] = "auto"
    DISPATCH_PROBE: ClassVar[bool] = True
    ENTITIES_PER_JOB_MIN: ClassVar[int] = 1
    ENTITIES_PER_JOB_MAX: ClassVar[int] = 500
    WORKER_MEMORY_FRACTION: ClassVar[float] = 0.85
    PREFETCH_AHEAD: ClassVar[int] = 1

    _runtime_tune: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def performance_baseline(cls) -> Dict[str, Any]:
        return {
            "reserve_cores": cls.RESERVE_CORES,
            "max_parallel_jobs_cap": cls.MAX_PARALLEL_JOBS_CAP,
            "memory_budget_mb": cls.MEMORY_BUDGET_MB,
            "memory_floor_mb": cls.MEMORY_FLOOR_MB,
            "entities_per_job": cls.ENTITIES_PER_JOB,
            "dispatch_probe": cls.DISPATCH_PROBE,
            "entities_per_job_min": cls.ENTITIES_PER_JOB_MIN,
            "entities_per_job_max": cls.ENTITIES_PER_JOB_MAX,
            "worker_memory_fraction": cls.WORKER_MEMORY_FRACTION,
            "prefetch_ahead": cls.PREFETCH_AHEAD,
        }

    @classmethod
    def apply_runtime_tune(cls, **kwargs: Any) -> None:
        cls._runtime_tune.update(kwargs)

    @classmethod
    def clear_runtime_tune(cls) -> None:
        cls._runtime_tune.clear()

    @classmethod
    def default_performance(cls) -> Dict[str, Any]:
        merged = cls.performance_baseline()
        if cls._runtime_tune:
            merged = EntityBasedPerformance.from_dict(merged).merge(cls._runtime_tune).to_dict()
        return resolve_entity_based_performance(merged)

    @staticmethod
    def entity_ids_from_jobs(jobs: list) -> List[str]:
        ids: List[str] = []
        for index, job in enumerate(jobs):
            if not isinstance(job, dict):
                raise ValueError(f"entity_based jobs[{index}] 须为 dict")
            if "entity_id" not in job:
                raise ValueError(f"entity_based jobs[{index}] 缺少 entity_id")
            entity_id = str(job["entity_id"]).strip()
            if not entity_id:
                raise ValueError(f"entity_based jobs[{index}].entity_id 不能为空")
            ids.append(entity_id)
        return ids

    @classmethod
    def assert_mode(cls, context: BacktestRuntimeContext) -> None:
        mode = BacktestMode.normalize(context.execution_mode)
        if mode != cls.EXECUTION_MODE.value:
            raise ValueError(
                f"期望 execution_mode={cls.EXECUTION_MODE.value!r}, "
                f"实际 {mode!r}"
            )

    @classmethod
    def from_strategy_context(
        cls,
        strategy: StrategyContext,
        *,
        execution_mode: str,
        jobs: List[Dict[str, Any]],
        task_name: str,
        run_name: str,
        performance: Dict[str, Any],
        global_data_meta: Optional[Dict[str, Any]] = None,
    ) -> EntityBasedRuntimeContext:
        base = BacktestRuntimeContext.from_strategy_context(
            strategy,
            execution_mode=execution_mode,
            jobs=jobs,
            task_name=task_name,
            run_name=run_name,
            performance=performance,
            global_data_meta=global_data_meta,
        )
        return cls(**base.__dict__)


__all__ = ["EntityBasedRuntimeContext"]
