"""entity_based job executor（enumerator的回调函数集合）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class JobExecutor:
    """entity_based job executor（enumerator的回调函数集合）。"""

    @staticmethod
    def on_child_process_task_start(job_context: Any) -> Dict[str, Any]:
        """子进程钩子：初始化 per entity contracts，batch load 降低 IO。"""
        logger.info("子进程task开始：job_id=%s", job_context.job_id)

        from core.modules.strategy.core.engines.enumerator.entity_based.services.batch_data_loader import (
            BatchDataLoader,
        )

        loaded_data = BatchDataLoader.load_bundle_data(job_context.payload)

        logger.info(
            "子进程task开始完成：entity_contracts_count=%d, global_keys=%d",
            len(loaded_data.get("entity_contracts", {})),
            len(loaded_data.get("global_data", {})),
        )

        return loaded_data

    @staticmethod
    def on_child_process_task_complete(job_context: Any) -> None:
        """子进程钩子：将缓冲的 opportunities 写入 CSV 后清空 buffer。"""
        from core.modules.strategy.core.engines.enumerator.entity_based.services.recorder import (
            EntityBasedEnumeratorRecorder,
        )

        EntityBasedEnumeratorRecorder.resolve(job_context.payload).flush_job_opportunities()

    @staticmethod
    def execute(job_context: Any) -> Dict[str, Any]:
        """执行函数：calendar 时间轴 + per-entity tracker 枚举。"""
        logger.info("子进程执行开始（entity_based模式）")

        payload = job_context.payload
        loaded_data = job_context.init or {}
        entity_contracts = loaded_data.get("entity_contracts", {})
        global_data = loaded_data.get("global_data", {})
        strategy_info = payload.get("strategy_info", {})
        settings_dict = payload.get("settings", {})
        entity_specified = payload.get("entity_specified", [])

        hooks_module_path = strategy_info.get("hooks_module_path")
        hooks_class_name = strategy_info.get("hooks_class_name")
        if not hooks_module_path or not hooks_class_name:
            logger.error("缺少hooks信息：hooks_module_path或hooks_class_name")
            return {"success": False, "opportunities_count": 0, "error": "缺少hooks信息"}

        try:
            import importlib

            hooks_module = importlib.import_module(hooks_module_path)
            hooks_class = getattr(hooks_module, hooks_class_name)
            hooks_instance = hooks_class()
        except Exception as exc:
            logger.error("加载hooks类失败：%s", exc, exc_info=True)
            return {"success": False, "opportunities_count": 0, "error": str(exc)}

        from core.modules.data_contract import DATA_KEY
        from core.modules.strategy.core.engines.enumerator.entity_based.services.enumeration_simulator import (
            EntityEnumerationSimulator,
        )
        from core.modules.strategy.core.engines.enumerator.entity_based.services.recorder import (
            EntityBasedEnumeratorRecorder,
        )
        from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
            StrategySettings,
        )

        try:
            settings_obj = StrategySettings.from_dict(settings_dict)
        except Exception as exc:
            logger.error("构建StrategySettings失败：%s", exc, exc_info=True)
            return {"success": False, "opportunities_count": 0, "error": str(exc)}

        calendar_data = global_data.get(DATA_KEY.TRADE_CALENDAR, [])
        open_dates = [
            str(item.get("date") or "").strip()
            for item in calendar_data
            if item.get("is_open")
        ]
        if not open_dates:
            logger.warning("calendar数据为空，无法遍历日期")
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

        recorder = EntityBasedEnumeratorRecorder.resolve(payload)
        recorder.buffer_opportunities(simulator.buffer_for_recorder())

        opportunities_count = simulator.total_recorded_count()
        logger.info("子进程执行完成：opportunities_count=%d", opportunities_count)

        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "entities_with_opportunities": simulator.entities_with_investments(),
        }

    @staticmethod
    def on_single_task_result(report: Any, progress: Any) -> None:
        """主进程钩子：单 task 结果回调。"""
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
            logger.error("Task失败：job_id=%s, error=%s", report.job_id, report.error or "Unknown error")

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


__all__ = ["JobExecutor"]
