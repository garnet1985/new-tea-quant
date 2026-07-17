"""slice_based job executor（mode 专有 execute + 共用钩子）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.executor_hooks import (
    ExecutorHooks,
    ExecutorHooksContext,
)

logger = logging.getLogger(__name__)


class JobExecutor:
    """slice_based job executor（BE 钩子 + execute_fn）。

    边界:
    - 负责: slice lifecycle + calendar_asof 枚举；共用钩子委托 ExecutorHooks
    - 不负责: Pipeline 编排、BE reader/preload 调度
    - 调用方: BacktestEngine.slice_based（via EnumeratorPipeline）

    BE.slice_based 只转发 ``on_single_task_result``，不跑子进程 init/release 钩子。
    因此 ``execute`` 内用 ``run_job_lifecycle`` 自行串联 start → body → complete。
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
            f"slice_open_days={getattr(plan, 'slice_open_days', '?')}, "
            f"reader_workers={getattr(plan, 'reader_workers', '?')}",
            flush=True,
        )

    @staticmethod
    def on_child_process_task_start(job_context: Any) -> Dict[str, Any]:
        return ExecutorHooks.load_bundle_data(job_context, log_label="slice task")

    @staticmethod
    def on_child_process_task_complete(job_context: Any) -> None:
        # Head-phase samples are official work — always flush.
        ExecutorHooks.flush_job_investments(job_context)

    @staticmethod
    def execute(job_context: Any) -> Dict[str, Any]:
        from core.modules.backtest_engine.core.shared.job_lifecycle import run_job_lifecycle

        return run_job_lifecycle(
            JobExecutor._execute_body,
            job_context,
            on_child_process_task_start=JobExecutor.on_child_process_task_start,
            on_child_process_task_complete=JobExecutor.on_child_process_task_complete,
        )

    @staticmethod
    def _execute_body(job_context: Any) -> Dict[str, Any]:
        from core.modules.strategy.core.engines.enumerator.shared.services.enum_job_perf import (
            EnumJobPerfRecorder,
        )

        logger.info("slice 执行开始（slice_based模式）")
        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("enumerate")

        payload = job_context.payload
        loaded_data = job_context.init or {}
        entity_contracts = loaded_data.get("entity_contracts", {})
        global_data = loaded_data.get("global_data", {})
        strategy_info = payload.get("strategy_info", {})
        settings_dict = payload.get("settings", {})

        hooks_instance, err = ExecutorHooks.load_hooks(strategy_info)
        if err is not None:
            perf.end("enumerate")
            return err

        from core.modules.strategy.core.engines.enumerator.shared.report_manager import (
            ReportManager,
        )
        from core.modules.strategy.core.engines.enumerator.slice_based.simulation import (
            SliceEnumerationSimulator,
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

        open_dates = JobExecutor._resolve_open_dates(payload, global_data)
        if not open_dates:
            logger.warning("open_dates 为空，无法遍历日期")
            perf.end("enumerate")
            return {"success": True, "opportunities_count": 0, "warning": "open_dates为空"}

        entity_ids = JobExecutor._resolve_entity_ids(payload)
        start_date = str(payload.get("start_date") or open_dates[0])
        end_date = str(payload.get("end_date") or open_dates[-1])

        simulator = SliceEnumerationSimulator(entity_ids)
        simulator.run(
            open_dates=open_dates,
            start_date=start_date,
            end_date=end_date,
            settings=settings_obj,
            hooks=hooks_instance,
            strategy_name=strategy_info.get("key", ""),
            entity_contracts=entity_contracts,
            global_data=global_data,
            payload=payload,
            perf=perf,
        )

        ReportManager.worker_buffer_opportunities(
            payload,
            simulator.buffer_for_recorder(),
        )

        perf.end("enumerate")
        opportunities_count = simulator.total_recorded_count()
        logger.info("slice 执行完成：opportunities_count=%d", opportunities_count)

        runtime_plan = simulator.slice_runtime_plan_dict()
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "entities_with_opportunities": simulator.entities_with_investments(),
            "entities_count": len(entity_ids),
            "performance_metrics": {
                "calendar_slice_runtime_plan": runtime_plan,
            },
        }

    @staticmethod
    def _resolve_open_dates(payload: Dict[str, Any], global_data: Dict[str, Any]) -> List[str]:
        raw = payload.get("open_dates")
        if isinstance(raw, list) and raw:
            return [str(day).strip() for day in raw if str(day).strip()]

        calendar = payload.get("backtest_calendar")
        if isinstance(calendar, dict):
            cal_dates = calendar.get("open_dates")
            if isinstance(cal_dates, list) and cal_dates:
                return [str(day).strip() for day in cal_dates if str(day).strip()]

        from core.modules.data_contract import DATA_KEY

        calendar_data = global_data.get(DATA_KEY.TRADE_CALENDAR, [])
        return [
            str(item.get("date") or "").strip()
            for item in calendar_data
            if item.get("is_open") and str(item.get("date") or "").strip()
        ]

    @staticmethod
    def _resolve_entity_ids(payload: Dict[str, Any]) -> List[str]:
        for key in ("entity_ids", "stock_ids"):
            raw = payload.get(key)
            if isinstance(raw, list) and raw:
                return [str(item).strip() for item in raw if str(item).strip()]
        specified = payload.get("entity_specified") or []
        return [
            str(item.get("id") or "").strip()
            for item in specified
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ]


__all__ = ["ExecutorHooksContext", "JobExecutor"]
