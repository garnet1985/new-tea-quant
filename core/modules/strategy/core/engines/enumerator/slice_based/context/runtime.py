"""slice_based 模式 runtime context（Layer 3 特化）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.performance import resolve_slice_based_performance

from core.modules.strategy.core.context.backtest_runtime import BacktestRuntimeContext
from core.modules.strategy.core.context.strategy_context import StrategyContext


@dataclass
class SliceBasedRuntimeContext(BacktestRuntimeContext):
    """slice_based 回测 runtime。"""

    EXECUTION_MODE: ClassVar[BacktestMode] = BacktestMode.SLICE_BASED

    READER_WORKERS: ClassVar[str] = "auto"
    QUEUE_DEPTH: ClassVar[str] = "auto"
    PREFETCH_ENABLED: ClassVar[bool] = True
    SLICE_OPEN_DAYS: ClassVar[str] = "auto"

    _runtime_tune: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def performance_baseline(cls) -> Dict[str, Any]:
        # Scheduling defaults live in SliceBasedPerformance (backtest_engine).
        # Only list strategy-side knobs that subclasses commonly override.
        return {
            "reader_workers": cls.READER_WORKERS,
            "queue_depth": cls.QUEUE_DEPTH,
            "prefetch_enabled": cls.PREFETCH_ENABLED,
            "slice_open_days": cls.SLICE_OPEN_DAYS,
        }

    @classmethod
    def apply_runtime_tune(cls, **kwargs: Any) -> None:
        cls._runtime_tune.update(kwargs)

    @classmethod
    def clear_runtime_tune(cls) -> None:
        cls._runtime_tune.clear()

    @classmethod
    def default_performance(cls) -> Dict[str, Any]:
        merged = dict(cls.performance_baseline())
        merged.update(cls._runtime_tune)
        return resolve_slice_based_performance(merged)

    @staticmethod
    def calendar_from_job(job: Dict[str, Any]) -> Dict[str, Any]:
        calendar = job.get("backtest_calendar")
        if not isinstance(calendar, dict):
            raise ValueError("slice_based job 缺少 backtest_calendar")
        return dict(calendar)

    @classmethod
    def open_dates_from_job(cls, job: Dict[str, Any]) -> List[str]:
        calendar = cls.calendar_from_job(job)
        open_dates = calendar.get("open_dates")
        if not isinstance(open_dates, list) or not open_dates:
            raise ValueError("backtest_calendar.open_dates 须为非空 list")
        return list(open_dates)

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
    ) -> SliceBasedRuntimeContext:
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


__all__ = ["SliceBasedRuntimeContext"]
