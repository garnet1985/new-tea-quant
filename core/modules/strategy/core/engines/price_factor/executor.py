"""价格回测 JobExecutor：子进程加载 CSV + 回放落盘（经 RunCallbacks）。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
    GoalAchievements,
    InvestmentRow,
    StockInvestments,
)
from core.modules.strategy.core.engines.price_factor.job_builder import JobBuilder
from core.modules.strategy.core.engines.price_factor.report_manager import (
    EntityInvestments,
    PriceInvestmentRow,
)

logger = logging.getLogger(__name__)


class JobExecutor:
    """价格回测唯一对外钩子面（生命周期 + 日历推进）。

    边界:
    - 负责: 读本 batch 枚举 CSV；task 结束时按锁仓规则回放并写 price entities CSV
    - 不负责: BE 调度/切 batch、overall 汇总（ReportManager.finalize）
    - 调用方: PriceFactorPipeline → ``callbacks=JobExecutor.build_run_callbacks()``

    说明:
    - v1 回放为 event-driven（信任枚举 entry/exit），在 ``on_after_task_complete`` 执行；
      ``on_tick`` 预留日历日推进（涨跌停重试等后续再填）。
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
        return cls._load_batch_enum_data(job_context)

    @classmethod
    def on_after_task_complete(cls, job_context: Any) -> None:
        cls._replay_and_save_batch(job_context)

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
        # 日历日推进（涨跌停延后卖出等）后续再实现；v1 在 after_task 事件回放
        _ = (job_context, point, index)

    # ── 私有：加载 / 回放 ──

    @classmethod
    def _load_batch_enum_data(cls, job_context: Any) -> Dict[str, Any]:
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
            "price_output_dir": str(meta.get("price_output_dir") or "").strip(),
            "end_date": str(meta.get("end_date") or "").strip(),
            "entities": entities,
        }

    @classmethod
    def _replay_and_save_batch(cls, job_context: Any) -> Dict[str, int]:
        """对本 batch 各 entity 做锁仓回放并写入 price version ``entities/``。"""
        init = job_context.init or {}
        entities = init.get("entities") or {}
        if not isinstance(entities, dict) or not entities:
            return {"entities": 0, "investments": 0}

        price_output_dir = str(init.get("price_output_dir") or "").strip()
        if not price_output_dir:
            payload = job_context.payload or {}
            meta = JobBuilder.price_factor_meta(payload)
            price_output_dir = str(meta.get("price_output_dir") or "").strip()
        if not price_output_dir:
            raise ValueError("price_output_dir 缺失：无法落盘价格投资记录")

        out_dir = Path(price_output_dir)
        end_date = str(init.get("end_date") or "").strip()
        if not end_date:
            payload = job_context.payload or {}
            meta = JobBuilder.price_factor_meta(payload)
            end_date = str(meta.get("end_date") or "").strip()

        total_inv = 0
        for entity_id, pack in entities.items():
            if not isinstance(pack, dict):
                continue
            stock_inv = pack.get("investments")
            rows = list(getattr(stock_inv, "rows", None) or [])
            price_rows = cls._replay_entity_investments(rows, backtest_end=end_date)
            EntityInvestments.save(out_dir, str(entity_id), price_rows)
            total_inv += len(price_rows)

        logger.info(
            "%s 回放落盘：job_id=%s entities=%d investments=%d → %s",
            cls.task_log_label,
            job_context.job_id,
            len(entities),
            total_inv,
            out_dir,
        )
        return {"entities": len(entities), "investments": total_inv}

    @staticmethod
    def _replay_entity_investments(
        investments: Sequence[InvestmentRow],
        *,
        backtest_end: str = "",
    ) -> List[PriceInvestmentRow]:
        """单 entity：枚举 investments → 买 1 / 锁仓 → PriceInvestmentRow。

        v1 信任枚举 entry/exit；只做无效买入过滤与同股锁仓。
        """
        ordered = sorted(
            list(investments or []),
            key=lambda row: (
                str(row.entry_date or row.trigger_date or "").strip(),
                str(row.investment_id or "").strip(),
            ),
        )
        holding_until: Optional[str] = None
        out: List[PriceInvestmentRow] = []
        end = str(backtest_end or "").strip()

        for row in ordered:
            buy_date = str(row.entry_date or "").strip()
            buy_price = float(row.entry_price or 0.0)
            if not buy_date or buy_price <= 0:
                continue

            if holding_until and buy_date <= holding_until:
                continue

            sell_date = str(row.exit_date or "").strip()
            sell_price = float(row.exit_price or 0.0)
            lifecycle = str(row.lifecycle or "").strip() or (
                "complete" if sell_date else "open"
            )
            result = str(row.result or "").strip()
            if not result and sell_date:
                if float(row.weighted_roi or 0.0) > 0:
                    result = "win"
                elif float(row.weighted_roi or 0.0) < 0:
                    result = "loss"

            out.append(
                PriceInvestmentRow(
                    opportunity_id=str(row.investment_id or "").strip(),
                    buy_date=buy_date,
                    buy_price=buy_price,
                    sell_date=sell_date,
                    sell_price=sell_price,
                    roi=float(row.weighted_roi or 0.0),
                    holding_days=int(row.holding_days or 0),
                    holding_trading_days=int(row.holding_days or 0),
                    exit_reason=str(row.exit_reason or "").strip(),
                    skip_reason="",
                    lifecycle=lifecycle,
                    result=result,
                )
            )

            if sell_date:
                holding_until = sell_date
            else:
                holding_until = end or buy_date

        return out

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
