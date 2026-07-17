"""entity_based job executor（mode 专有 execute + 共用钩子）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.executor_hooks import (
    ExecutorHooks,
    ExecutorHooksContext,
)

logger = logging.getLogger(__name__)


class JobExecutor:
    """entity_based job executor（BE 钩子 + execute_fn）。

    边界:
    - 负责: entity 日循环枚举模拟；共用钩子委托 ExecutorHooks
    - 不负责: Pipeline 编排、BE 进程池调度
    - 调用方: BacktestEngine.entity_based（via EnumeratorPipeline）
    """

    @staticmethod
    def build_run_callbacks(ctx: ExecutorHooksContext) -> Any:
        return ExecutorHooks.build_run_callbacks(
            ctx,
            on_before_all_tasks_start=JobExecutor.on_before_all_tasks_start,
            on_child_process_task_start=JobExecutor.on_child_process_task_start,
            on_child_process_task_complete=JobExecutor.on_child_process_task_complete,
            on_after_all_tasks_complete=ExecutorHooks.on_after_all_tasks_complete,
            on_single_task_result=ExecutorHooks.on_single_task_result,
        )

    @staticmethod
    def on_before_all_tasks_start(plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"~{getattr(plan, 'entities_per_job', '?')} entities/job, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @staticmethod
    def on_child_process_task_start(job_context: Any) -> Dict[str, Any]:
        return ExecutorHooks.load_bundle_data(job_context, log_label="子进程task")

    @staticmethod
    def on_child_process_task_complete(job_context: Any) -> None:
        if job_context.payload.get("_dispatch_probe"):
            return
        ExecutorHooks.flush_job_investments(job_context)

    @staticmethod
    def execute(job_context: Any) -> Dict[str, Any]:
        """执行函数：calendar 时间轴 + per-entity tracker 枚举。"""
        from core.modules.strategy.core.engines.enumerator.shared.services.enum_job_perf import (
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

        hooks_instance, err = ExecutorHooks.load_hooks(strategy_info)
        if err is not None:
            perf.end("enumerate")
            return err

        from core.modules.data_contract import DATA_KEY
        from core.modules.strategy.core.engines.enumerator.entity_based.simulation import (
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
            perf=perf,
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


__all__ = ["ExecutorHooksContext", "JobExecutor"]
