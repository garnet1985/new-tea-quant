"""enumerator JobExecutor 基类（entity / slice 共用）。

本文件:
- BaseJobExecutor: RunCallbacks 组装、bundle load、flush、进度
- ExecutorHooksContext: 主进程钩子上下文（可 pickle 的 ClassVar）
  边界: 骨架与周边；日业务由子类钩子实现，状态只进 ``job_context.init``
  勿在此恢复 JobSession 委托层
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorHooksContext:
    """JobExecutor 构建 RunCallbacks 时的主进程上下文。

    边界:
    - 负责: 携带 ReportManager / GlobalEntityCache 引用给钩子闭包
    - 不负责: 执行或落盘本身
    - 调用方: EnumeratorPipeline → mode JobExecutor.build_run_callbacks
    """

    report_manager: Any = None
    global_entity_cache: Any = None


class BaseJobExecutor:
    """entity / slice JobExecutor 基类。

    边界:
    - 负责: RunCallbacks 组装、bundle load、flush、进度
    - 日业务: 子类覆盖 ``on_before_task_start`` / ``on_tick`` / ``on_ticks_complete``，
      可变状态挂在 BE ``job_context.init``
    - 调用方: entity_based / slice_based JobExecutor
    """

    task_log_label: str = "task"
    #: Bound PipelineProgress.pipeline_name this executor may tick (None = never).
    progress_pipeline_name: ClassVar[Optional[str]] = "enum"
    #: 主进程钩子上下文（避免 lambda，保证 RunCallbacks 可 pickle）
    _hooks_ctx: ClassVar[Optional[ExecutorHooksContext]] = None

    @classmethod
    def build_run_callbacks(cls, ctx: ExecutorHooksContext) -> Any:
        from core.modules.backtest_engine.contracts import RunCallbacks
        from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
            JobBundleLoader,
        )

        cls._hooks_ctx = ctx
        return RunCallbacks(
            on_before_all_tasks_start=cls.on_before_all_tasks_start,
            on_before_task_start=cls.on_before_task_start,
            on_after_task_complete=cls.on_after_task_complete,
            on_after_all_tasks_complete=cls._dispatch_after_all_tasks_complete,
            on_task_result=cls._dispatch_task_result,
            on_tick=cls.on_tick,
            on_ticks_complete=cls.on_ticks_complete,
            load_per_entity_window=JobBundleLoader.load_per_entity_window,
        )

    @classmethod
    def _dispatch_after_all_tasks_complete(cls, job_reports: List[Any]) -> None:
        ctx = cls._hooks_ctx
        cache = ctx.global_entity_cache if ctx is not None else None
        cls.on_after_all_tasks_complete(job_reports, cache)

    @classmethod
    def _dispatch_task_result(cls, report: Any, progress: Any) -> None:
        ctx = cls._hooks_ctx
        report_manager = ctx.report_manager if ctx is not None else None
        cls.on_task_result(report, progress, report_manager=report_manager)

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @classmethod
    def on_before_task_start(cls, job_context: Any) -> Dict[str, Any]:
        return cls.load_bundle_data(job_context, log_label=cls.task_log_label)

    @classmethod
    def on_after_task_complete(cls, job_context: Any) -> None:
        cls.flush_job_investments(job_context)

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        raise NotImplementedError(f"{cls.__name__} 须覆盖 on_tick")

    @classmethod
    def on_ticks_complete(cls, job_context: Any, timeline: Any) -> Dict[str, Any]:
        raise NotImplementedError(f"{cls.__name__} 须覆盖 on_ticks_complete")

    @classmethod
    def load_bundle_data(cls, job_context: Any, *, log_label: str) -> Dict[str, Any]:
        from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
            JobBundleLoader,
        )
        from core.modules.strategy.core.engines.enumerator.common.performance_tracker.performance_tracker import (
            EnumJobPerfRecorder,
        )

        logger.info("%s开始：job_id=%s", log_label, job_context.job_id)
        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("load_data")
        loaded_data = JobBundleLoader.load(job_context.payload, perf=perf)
        perf.end("load_data")
        logger.info(
            "%s完成：entity_contracts_count=%d, global_keys=%d",
            log_label,
            len(loaded_data.get("entity_contracts", {})),
            len(loaded_data.get("global_data", {})),
        )
        return loaded_data

    @classmethod
    def flush_job_investments(cls, job_context: Any) -> None:
        from core.modules.strategy.core.engines.enumerator.common.performance_tracker.performance_tracker import (
            EnumJobPerfRecorder,
        )
        from core.modules.strategy.core.engines.enumerator.common.report_manager import (
            ReportManager,
        )

        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("flush_csv")
        ReportManager.worker_flush_job_investments(job_context.payload)
        perf.end("flush_csv")

    @classmethod
    def on_task_result(
        cls,
        report: Any,
        progress: Any,
        *,
        report_manager: Optional[Any] = None,
    ) -> None:
        if report_manager is not None:
            report_manager.profiler.collect(report)

        try:
            from core.modules.strategy.core.services.progress import PipelineProgress

            name = cls.progress_pipeline_name
            if name and PipelineProgress.drives_pipeline(name):
                PipelineProgress.tick_from_run_progress(progress)
        except Exception:
            logger.exception("PipelineProgress.tick_from_run_progress failed")

        logger.info(
            "Task完成进度：%s/%s (成功=%s, 失败=%s)",
            progress.finished,
            progress.total,
            progress.ok,
            progress.fail,
        )
        logger.info("Task报告：job_id=%s, success=%s", report.job_id, report.success)
        if report.success and report.data:
            count = int(report.data.get("opportunities_count") or 0)
            logger.info("Task opportunities_count=%d", count)
        if not report.success:
            logger.error(
                "Task失败：job_id=%s, error=%s",
                report.job_id,
                report.error or "Unknown error",
            )

    @classmethod
    def on_after_all_tasks_complete(
        cls,
        job_reports: List[Any],
        global_entity_cache: Any = None,
    ) -> None:
        logger.info("所有tasks完成：total=%d", len(job_reports))

        if global_entity_cache:
            try:
                global_entity_cache.cleanup()
                logger.info("全局缓存清理完成")
            except Exception as exc:
                logger.warning("清理全局缓存失败：%s", exc)

        success_count = sum(1 for report in job_reports if report.success)
        fail_count = len(job_reports) - success_count
        logger.info(
            "最终统计：total=%d, success=%d, fail=%d",
            len(job_reports),
            success_count,
            fail_count,
        )

    @classmethod
    def load_hooks(
        cls,
        strategy_info: Dict[str, Any],
        settings: Any = None,
    ) -> Any:
        """加载 ``StrategyHookRuntime``；失败返回 (None, error_dict)。"""
        from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
            StrategySettings,
        )
        from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime

        resolved = settings
        if resolved is None:
            resolved = StrategySettings.from_dict({})
        elif not isinstance(resolved, StrategySettings):
            resolved = StrategySettings.from_dict(dict(resolved or {}))
        return StrategyHookRuntime.from_strategy_info(strategy_info, resolved)


__all__ = ["ExecutorHooksContext", "BaseJobExecutor"]
