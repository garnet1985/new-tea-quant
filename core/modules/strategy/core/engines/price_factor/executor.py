"""价格回测 JobExecutor：子进程加载 CSV + 日历 on_tick（经 RunCallbacks）。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
    GoalAchievements,
    StockInvestments,
)
from core.modules.strategy.core.engines.price_factor.job_builder import JobBuilder

logger = logging.getLogger(__name__)


class JobExecutor:
    """价格回测唯一对外钩子面（生命周期 + 日历推进）。

    边界:
    - 负责: on_before_task_start 读本 batch CSV；on_tick 按日推进（业务后续填）
    - 不负责: BE 调度/切 batch、报告落盘
    - 调用方: PriceFactorPipeline → ``callbacks=JobExecutor.build_run_callbacks()``
    """

    task_log_label = "price_factor task"

    @classmethod
    def build_run_callbacks(cls) -> RunCallbacks:
        return RunCallbacks(
            on_before_all_tasks_start=cls.on_before_all_tasks_start,
            on_before_task_start=cls.on_before_task_start,
            on_after_task_complete=cls.on_after_task_complete,
            on_after_all_tasks_complete=cls.on_after_all_tasks_complete,
            on_task_result=cls.on_task_result,
            on_tick=cls.on_tick,
        )

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"~{getattr(plan, 'entities_per_job', '?')} entities/job, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @classmethod
    def on_before_task_start(cls, job_context: Any) -> Dict[str, Any]:
        return cls.load_batch_enum_data(job_context)

    @classmethod
    def on_after_task_complete(cls, job_context: Any) -> None:
        _ = job_context

    @classmethod
    def on_after_all_tasks_complete(cls, job_reports: List[Any]) -> None:
        logger.info("price_factor 全部 task 完成：total=%d", len(job_reports))

    @classmethod
    def on_task_result(cls, report: Any, progress: Any) -> None:
        logger.info(
            "price_factor 进度：%s/%s (ok=%s, fail=%s) job_id=%s success=%s",
            progress.finished,
            progress.total,
            progress.ok,
            progress.fail,
            report.job_id,
            report.success,
        )
        if not report.success:
            logger.error(
                "price_factor task 失败：job_id=%s error=%s",
                report.job_id,
                report.error or "Unknown error",
            )

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        # 业务回放（买 1 股 / 锁仓）后续步骤再实现
        _ = (job_context, point, index)

    @classmethod
    def load_batch_enum_data(cls, job_context: Any) -> Dict[str, Any]:
        """读本 batch entity 的枚举 CSV → ``job_context.init``。"""
        payload = job_context.payload or {}
        meta = JobBuilder.price_factor_meta(payload)
        enum_dir = Path(str(meta.get("enum_output_dir") or "")).expanduser()
        if not enum_dir.is_dir():
            raise FileNotFoundError(f"enum_output_dir 不存在: {enum_dir}")

        entity_ids = cls._entity_ids_from_payload(payload)
        logger.info(
            "%s 加载枚举 CSV：job_id=%s entities=%d dir=%s",
            cls.task_log_label,
            job_context.job_id,
            len(entity_ids),
            enum_dir,
        )

        entities: Dict[str, Dict[str, Any]] = {}
        for entity_id in entity_ids:
            entities[entity_id] = {
                "investments": StockInvestments.load(enum_dir, entity_id),
                "goals": GoalAchievements.load(enum_dir, entity_id),
            }

        return {
            "enum_output_dir": str(enum_dir),
            "entities": entities,
        }

    @staticmethod
    def _entity_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        specified = payload.get("entity_specified") or []
        if not isinstance(specified, list):
            raise ValueError("payload.entity_specified 必须是 list")
        out: List[str] = []
        for item in specified:
            if not isinstance(item, dict):
                continue
            entity_id = str(item.get("id") or "").strip()
            if entity_id:
                out.append(entity_id)
        return out


__all__ = ["JobExecutor"]
