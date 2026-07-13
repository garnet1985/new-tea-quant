"""entity_based job executor（enumerator 的回调函数集合）。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorHooksContext:
    """JobExecutor 构建 RunCallbacks 时的主进程上下文。"""

    report_manager: Any = None
    global_entity_cache: Any = None


class JobExecutor:
    """entity_based job executor（enumerator 的回调函数集合）。"""

    @staticmethod
    def build_run_callbacks(ctx: ExecutorHooksContext) -> Any:
        """组装 BacktestEngine RunCallbacks（主进程 + 子进程钩子）。"""
        from core.modules.backtest_engine.contracts import RunCallbacks

        return RunCallbacks(
            on_before_all_tasks_start=JobExecutor.on_before_all_tasks_start,
            on_child_process_task_start=JobExecutor.on_child_process_task_start,
            on_child_process_task_complete=JobExecutor.on_child_process_task_complete,
            on_after_all_tasks_complete=lambda job_reports: JobExecutor.on_after_all_tasks_complete(
                job_reports,
                ctx.global_entity_cache,
            ),
            on_single_task_result=lambda report, progress: JobExecutor.on_single_task_result(
                report,
                progress,
                report_manager=ctx.report_manager,
            ),
        )

    @staticmethod
    def on_before_all_tasks_start(plan: Any, batches: List[Any]) -> None:
        """主进程钩子：调度 plan 就绪后打印摘要。"""
        print(
            f"  调度: {len(batches)} batches, "
            f"~{getattr(plan, 'entities_per_job', '?')} entities/job, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @staticmethod
    def on_child_process_task_start(job_context: Any) -> Dict[str, Any]:
        """子进程钩子：初始化 per entity contracts，batch load 降低 IO。"""
        from core.modules.strategy.core.engines.enumerator.entity_based.services.enum_job_perf import (
            EnumJobPerfRecorder,
        )

        logger.info("子进程task开始：job_id=%s", job_context.job_id)
        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("load_data")

        from core.modules.strategy.core.engines.enumerator.entity_based.services.batch_data_loader import (
            BatchDataLoader,
        )

        loaded_data = BatchDataLoader.load_bundle_data(job_context.payload)
        perf.end("load_data")

        logger.info(
            "子进程task开始完成：entity_contracts_count=%d, global_keys=%d",
            len(loaded_data.get("entity_contracts", {})),
            len(loaded_data.get("global_data", {})),
        )

        return loaded_data

    @staticmethod
    def on_child_process_task_complete(job_context: Any) -> None:
        """子进程钩子：将缓冲的 opportunities 写入 CSV 后清空 buffer。"""
        if job_context.payload.get("_dispatch_probe"):
            return
        from core.modules.strategy.core.engines.enumerator.entity_based.services.enum_job_perf import (
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
    def execute(job_context: Any) -> Dict[str, Any]:
        """执行函数：calendar 时间轴 + per-entity tracker 枚举。"""
        from core.modules.strategy.core.engines.enumerator.entity_based.services.enum_job_perf import (
            EnumJobPerfRecorder,
        )

        logger.info("子进程执行开始（entity_based模式）")
        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("enumerate")

        payload = job_context.payload
        loaded_data = job_context.init or {}
        entity_contracts = loaded_data.get("entity_contracts", {})
        global_data = loaded_data.get("global_data", {})
        strategy_info = payload.get("strategy_info", {})
        settings_dict = payload.get("settings", {})
        entity_specified = payload.get("entity_specified", [])

        hooks_module_path = strategy_info.get("hooks_module_path")
        hooks_class_name = strategy_info.get("hooks_class_name")
        hooks_file_path = strategy_info.get("hooks_file_path", "")
        if not hooks_module_path or not hooks_class_name:
            logger.error("缺少hooks信息：hooks_module_path或hooks_class_name")
            perf.end("enumerate")
            return {"success": False, "opportunities_count": 0, "error": "缺少hooks信息"}

        try:
            from core.modules.strategy.core.services.discovery.worker_loader import (
                StrategyWorkerLoader,
            )

            hooks_class = StrategyWorkerLoader.import_hooks_class(
                worker_module_path=hooks_module_path,
                worker_class_name=hooks_class_name,
                worker_file_path=str(hooks_file_path or ""),
            )
            hooks_instance = hooks_class()
        except Exception as exc:
            logger.error("加载hooks类失败：%s", exc, exc_info=True)
            perf.end("enumerate")
            return {"success": False, "opportunities_count": 0, "error": str(exc)}

        from core.modules.data_contract import DATA_KEY
        from core.modules.strategy.core.engines.enumerator.entity_based.services.enumeration_simulator import (
            EntityEnumerationSimulator,
        )
        from core.modules.strategy.core.engines.enumerator.shared.report_manager import (
            ReportManager,
        )
        from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
            StrategySettings,
        )

        try:
            settings_obj = StrategySettings.from_dict(settings_dict)
        except Exception as exc:
            logger.error("构建StrategySettings失败：%s", exc, exc_info=True)
            perf.end("enumerate")
            return {"success": False, "opportunities_count": 0, "error": str(exc)}

        calendar_data = global_data.get(DATA_KEY.TRADE_CALENDAR, [])
        open_dates = [
            str(item.get("date") or "").strip()
            for item in calendar_data
            if item.get("is_open")
        ]
        if not open_dates:
            logger.warning("calendar数据为空，无法遍历日期")
            perf.end("enumerate")
            return {"success": True, "opportunities_count": 0, "warning": "calendar数据为空"}

        entity_shared = payload.get("entity_shared", {})
        first_data_key_params = list(entity_shared.values())[0] if entity_shared else {}
        start_date = first_data_key_params.get("start", open_dates[0])
        end_date = first_data_key_params.get("end", open_dates[-1])

        entity_ids = [
            str(item.get("id") or "").strip()
            for item in entity_specified
            if str(item.get("id") or "").strip()
        ]
        simulator = EntityEnumerationSimulator(entity_ids)
        simulator.run(
            open_dates=open_dates,
            start_date=str(start_date),
            end_date=str(end_date),
            settings=settings_obj,
            hooks=hooks_instance,
            strategy_name=strategy_info.get("key", ""),
            entity_contracts=entity_contracts,
            global_data=global_data,
            entity_specified=entity_specified,
        )

        if not payload.get("_dispatch_probe"):
            ReportManager.worker_buffer_opportunities(
                payload,
                simulator.buffer_for_recorder(),
            )

        perf.end("enumerate")
        opportunities_count = simulator.total_recorded_count()
        logger.info("子进程执行完成：opportunities_count=%d", opportunities_count)

        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "entities_with_opportunities": simulator.entities_with_investments(),
            "entities_count": len(entity_specified),
        }

    @staticmethod
    def on_single_task_result(
        report: Any,
        progress: Any,
        *,
        report_manager: Optional[Any] = None,
    ) -> None:
        """主进程钩子：单 task 完成（进度日志 + profiler 采集）。"""
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
    def on_after_all_tasks_complete(job_reports: List[Any], global_entity_cache: Any = None) -> None:
        """主进程钩子：全局清理。"""
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


__all__ = ["ExecutorHooksContext", "JobExecutor"]
