"""公共 JobExecutor 钩子（entity / slice 共用主进程回调与 load/flush）。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

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


class ExecutorHooks:
    """entity / slice JobExecutor 共用的主进程钩子与数据加载。

    边界:
    - 负责: callbacks 组装、batch load、flush CSV、单 task 进度、全局 cleanup
    - 不负责: mode 专有日业务（EntityAdvancementHooks / SliceAdvancementHooks）
    - 调用方: entity_based.JobExecutor / slice_based.JobExecutor
    """

    @staticmethod
    def build_run_callbacks(
        ctx: ExecutorHooksContext,
        *,
        on_before_all_tasks_start: Callable[[Any, List[Any]], None],
        on_before_task_start: Callable[[Any], Dict[str, Any]],
        on_after_task_complete: Callable[[Any], None],
        on_after_all_tasks_complete: Callable[..., None],
        on_task_result: Callable[..., None],
    ) -> Any:
        from core.modules.backtest_engine.contracts import RunCallbacks

        return RunCallbacks(
            on_before_all_tasks_start=on_before_all_tasks_start,
            on_before_task_start=on_before_task_start,
            on_after_task_complete=on_after_task_complete,
            on_after_all_tasks_complete=lambda job_reports: on_after_all_tasks_complete(
                job_reports,
                ctx.global_entity_cache,
            ),
            on_task_result=lambda report, progress: on_task_result(
                report,
                progress,
                report_manager=ctx.report_manager,
            ),
        )

    @staticmethod
    def load_bundle_data(job_context: Any, *, log_label: str) -> Dict[str, Any]:
        from core.modules.strategy.core.engines.enumerator.shared.services.batch_data_loader import (
            BatchDataLoader,
        )
        from core.modules.strategy.core.engines.enumerator.shared.services.enum_job_perf import (
            EnumJobPerfRecorder,
        )

        logger.info("%s开始：job_id=%s", log_label, job_context.job_id)
        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("load_data")
        loaded_data = BatchDataLoader.load_bundle_data(job_context.payload, perf=perf)
        perf.end("load_data")
        logger.info(
            "%s完成：entity_contracts_count=%d, global_keys=%d",
            log_label,
            len(loaded_data.get("entity_contracts", {})),
            len(loaded_data.get("global_data", {})),
        )
        return loaded_data

    @staticmethod
    def flush_job_investments(job_context: Any) -> None:
        from core.modules.strategy.core.engines.enumerator.shared.services.enum_job_perf import (
            EnumJobPerfRecorder,
        )
        from core.modules.strategy.core.engines.enumerator.shared.report_manager import (
            ReportManager,
        )

        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("flush_csv")
        ReportManager.worker_flush_job_investments(job_context.payload)
        perf.end("flush_csv")

    @staticmethod
    def on_task_result(
        report: Any,
        progress: Any,
        *,
        report_manager: Optional[Any] = None,
    ) -> None:
        if report_manager is not None:
            report_manager.profiler.collect(report)

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

    @staticmethod
    def on_after_all_tasks_complete(
        job_reports: List[Any], global_entity_cache: Any = None
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

    @staticmethod
    def load_hooks(strategy_info: Dict[str, Any]) -> Any:
        """加载策略 hooks 类实例；失败返回 (None, error_dict)。"""
        hooks_module_path = strategy_info.get("hooks_module_path")
        hooks_class_name = strategy_info.get("hooks_class_name")
        hooks_file_path = strategy_info.get("hooks_file_path", "")
        if not hooks_module_path or not hooks_class_name:
            return None, {"success": False, "opportunities_count": 0, "error": "缺少hooks信息"}

        try:
            from core.modules.strategy.core.services.discovery.worker_loader import (
                StrategyWorkerLoader,
            )

            hooks_class = StrategyWorkerLoader.import_hooks_class(
                worker_module_path=hooks_module_path,
                worker_class_name=hooks_class_name,
                worker_file_path=str(hooks_file_path or ""),
            )
            return hooks_class(), None
        except Exception as exc:
            logger.error("加载hooks类失败：%s", exc, exc_info=True)
            return None, {"success": False, "opportunities_count": 0, "error": str(exc)}


__all__ = ["ExecutorHooksContext", "ExecutorHooks"]
