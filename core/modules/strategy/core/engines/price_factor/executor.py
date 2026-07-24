"""价格回测 JobExecutor — worker 读 enum CSV + 成交回放落盘。

本文件:
- JobExecutor: RunCallbacks；task 结束写 price entities CSV
  边界: 负责 worker 内回放与 deferred exit；不负责 BE 切 batch、overall 汇总
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.market_profile.core.markets import create_market_rules
from core.modules.strategy.core.engines.shared.services.simulation_input.stock_investments import (
    GoalAchievementRow,
    GoalAchievements,
    InvestmentRow,
    StockInvestments,
)
from core.modules.strategy.core.engines.price_factor.helpers import (
    load_stock_klines,
    position_fully_closed,
    resolve_holding_until,
    retry_deferred_exits,
)
from core.modules.strategy.core.engines.price_factor.job_builder import JobBuilder
from core.modules.strategy.core.engines.price_factor.report_manager import (
    EntityInvestments,
    PriceInvestmentRow,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)

logger = logging.getLogger(__name__)

_DEFAULT_MARKET_PROFILE = "china_a_stock"


class JobExecutor:
    """价格回测唯一对外钩子面（生命周期 + 日历推进）。

    边界:
    - 负责: 读本 batch 枚举 CSV；task 结束时按锁仓规则回放并写 price entities CSV
    - 不负责: BE 调度/切 batch、overall 汇总（ReportManager.finalize）
    - 调用方: PriceFactorPipeline → ``callbacks=JobExecutor.build_run_callbacks()``

    说明:
    - 回放为 event-driven（信任枚举 entry；exit 遇跌停挡板时顺延重试），在
      ``on_after_task_complete`` 执行；``on_tick`` 暂 noop（全日历状态机后续再迁）。
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
        # 全日历 day-driven 状态机后续再迁；跌停顺延卖出已在 after_task 事件回放中处理
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

        settings_raw = (
            (job_context.payload or {}).get("settings")
            if isinstance(job_context.payload, dict)
            else None
        )
        settings_dict = dict(settings_raw) if isinstance(settings_raw, dict) else {}
        strategy = StrategySettings.from_dict(settings_dict)
        market_profile = (
            str(settings_dict.get("market_profile") or "").strip()
            or _DEFAULT_MARKET_PROFILE
        )
        try:
            market_rules = create_market_rules(market_profile)
        except Exception as exc:
            logger.warning(
                "create_market_rules(%s) 失败，跌停重试仅信 enum 标记: %s",
                market_profile,
                exc,
            )
            market_rules = None

        total_inv = 0
        skipped_exit_at_limit = 0
        for entity_id, pack in entities.items():
            if not isinstance(pack, dict):
                continue
            stock_inv = pack.get("investments")
            rows = list(getattr(stock_inv, "rows", None) or [])
            goals_pack = pack.get("goals")
            goal_rows = list(getattr(goals_pack, "rows", None) or [])
            price_rows, skip_sell = cls._replay_entity_investments(
                rows,
                entity_id=str(entity_id),
                backtest_end=end_date,
                settings=strategy,
                goal_rows=goal_rows,
                market_rules=market_rules,
            )
            EntityInvestments.save(out_dir, str(entity_id), price_rows)
            total_inv += len(price_rows)
            skipped_exit_at_limit += skip_sell

        logger.info(
            "%s 回放落盘：job_id=%s entities=%d investments=%d "
            "skipped_exit_at_limit=%d → %s",
            cls.task_log_label,
            job_context.job_id,
            len(entities),
            total_inv,
            skipped_exit_at_limit,
            out_dir,
        )
        return {
            "entities": len(entities),
            "investments": total_inv,
            "skipped_exit_at_limit": skipped_exit_at_limit,
        }

    @staticmethod
    def _replay_entity_investments(
        investments: Sequence[InvestmentRow],
        *,
        entity_id: str = "",
        backtest_end: str = "",
        settings: Optional[StrategySettings] = None,
        goal_rows: Optional[Sequence[GoalAchievementRow]] = None,
        market_rules: Any = None,
        load_klines=None,
    ) -> Tuple[List[PriceInvestmentRow], int]:
        """单 entity：枚举 investments → 买 1 / 锁仓 / 跌停顺延卖出 → PriceInvestmentRow。

        返回 ``(rows, skipped_exit_at_limit)``。
        """
        strategy = settings or StrategySettings.from_dict({})
        sim = strategy.simulation
        control = sim.risk_control
        allow_enter_at_limit_up = bool(sim.allow_enter_at_limit_up)
        allow_exit_at_limit_down = bool(sim.allow_exit_at_limit_down)
        kline_loader = load_klines or load_stock_klines
        goals_by_inv = _index_goals_by_investment(goal_rows or [])
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
        skipped_sell = 0
        sid = str(entity_id or "").strip()

        for row in ordered:
            if control.should_skip_enter(status_tags=row.stock_status_at_trigger):
                continue

            enter_date = str(row.entry_date or "").strip()
            enter_price = float(row.entry_price or 0.0)
            if not enter_date or enter_price <= 0:
                continue

            if holding_until and enter_date <= holding_until:
                continue

            if row.enter_at_limit is True and not allow_enter_at_limit_up:
                continue

            inv_id = str(row.investment_id or "").strip()
            legs = _build_exit_legs(row, goals_by_inv.get(inv_id) or [])

            processed: List[Dict[str, Any]] = []
            skipped_legs: List[Dict[str, Any]] = []
            for leg in legs:
                if (
                    leg.get("exit_at_limit") is True
                    and not allow_exit_at_limit_down
                ):
                    skipped_sell += 1
                    skipped_legs.append(leg)
                    continue
                processed.append(leg)

            pending = None
            if skipped_legs and not position_fully_closed(processed):
                klines = kline_loader(
                    sid,
                    start_date=enter_date,
                    end_date=end or enter_date,
                )
                processed, pending, defer_skips = retry_deferred_exits(
                    enter_price=enter_price,
                    processed_legs=processed,
                    skipped_legs=skipped_legs,
                    klines=klines,
                    entity_id=sid,
                    settings=strategy,
                    market_rules=market_rules,
                )
                skipped_sell += int(defer_skips or 0)

            holding_until = resolve_holding_until(
                processed_legs=processed,
                enter_date=enter_date,
                backtest_end_date=end,
            )

            out.append(
                _to_price_row(
                    row=row,
                    enter_date=enter_date,
                    enter_price=enter_price,
                    processed=processed,
                    pending=pending,
                )
            )

        return out, skipped_sell

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


def _index_goals_by_investment(
    goal_rows: Sequence[GoalAchievementRow],
) -> Dict[str, List[GoalAchievementRow]]:
    out: Dict[str, List[GoalAchievementRow]] = {}
    for g in goal_rows or []:
        inv_id = str(getattr(g, "investment_id", "") or "").strip()
        if not inv_id:
            continue
        out.setdefault(inv_id, []).append(g)
    for legs in out.values():
        legs.sort(key=lambda r: str(r.date or ""))
    return out


def _build_exit_legs(
    row: InvestmentRow,
    goal_legs: Sequence[GoalAchievementRow],
) -> List[Dict[str, Any]]:
    """goals 非空按腿；否则退化为单笔 InvestmentRow exit。"""
    if goal_legs:
        legs: List[Dict[str, Any]] = []
        exit_date = str(row.exit_date or "").strip()
        for g in goal_legs:
            day = str(g.date or "").strip()
            flag: Optional[bool] = None
            if len(goal_legs) == 1 or (exit_date and day == exit_date):
                flag = row.exit_at_limit
            legs.append(
                {
                    "date": day,
                    "exit_date": day,
                    "exit_price": float(g.price or 0.0),
                    "exit_ratio": float(g.exit_ratio or 0.0) or 1.0,
                    "reason": str(g.reason or "").strip(),
                    "exit_at_limit": flag,
                }
            )
        return legs

    exit_date = str(row.exit_date or "").strip()
    if not exit_date:
        return []
    return [
        {
            "date": exit_date,
            "exit_date": exit_date,
            "exit_price": float(row.exit_price or 0.0),
            "exit_ratio": 1.0,
            "reason": str(row.exit_reason or "").strip(),
            "exit_at_limit": row.exit_at_limit,
        }
    ]


def _leg_date(leg: Dict[str, Any]) -> str:
    return str(leg.get("date") or leg.get("exit_date") or "").strip()


def _aggregate_roi(processed: List[Dict[str, Any]], enter_price: float) -> float:
    basis = float(enter_price or 0.0)
    if basis <= 0 or not processed:
        return 0.0
    remaining = 1.0
    weighted_profit = 0.0
    ordered = sorted(processed, key=_leg_date)
    for leg in ordered:
        try:
            ratio = float(leg.get("exit_ratio") or 0.0)
        except (TypeError, ValueError):
            ratio = 0.0
        if ratio <= 0:
            continue
        ratio = min(ratio, 1.0)
        sold = remaining * ratio
        try:
            sell_px = float(leg.get("exit_price") or 0.0)
        except (TypeError, ValueError):
            sell_px = 0.0
        weighted_profit += (sell_px - basis) * sold
        remaining *= max(0.0, 1.0 - ratio)
    return weighted_profit / basis


def _to_price_row(
    *,
    row: InvestmentRow,
    enter_date: str,
    enter_price: float,
    processed: List[Dict[str, Any]],
    pending: Any,
) -> PriceInvestmentRow:
    closed = position_fully_closed(processed)
    if closed:
        last = max(processed, key=_leg_date)
        exit_date = _leg_date(last)
        exit_price = float(last.get("exit_price") or 0.0)
        roi = _aggregate_roi(processed, enter_price)
        exit_reason = str(last.get("reason") or row.exit_reason or "").strip()
        lifecycle = "complete"
        if roi > 0:
            result = "win"
        elif roi < 0:
            result = "loss"
        else:
            result = str(row.result or "").strip()
    else:
        exit_date = ""
        exit_price = 0.0
        roi = 0.0
        if pending is not None:
            exit_reason = str(getattr(pending, "reason", "") or row.exit_reason or "").strip()
        else:
            exit_reason = str(row.exit_reason or "").strip()
        lifecycle = "open"
        result = ""

    holding_days = int(row.holding_days or 0)
    if closed and exit_date and enter_date and len(enter_date) == 8 and len(exit_date) == 8:
        try:
            from datetime import datetime

            d0 = datetime.strptime(enter_date, "%Y%m%d")
            d1 = datetime.strptime(exit_date, "%Y%m%d")
            holding_days = max(0, (d1 - d0).days)
        except ValueError:
            pass

    return PriceInvestmentRow(
        opportunity_id=str(row.investment_id or "").strip(),
        enter_date=enter_date,
        enter_price=enter_price,
        exit_date=exit_date,
        exit_price=exit_price,
        roi=roi,
        holding_days=holding_days,
        holding_trading_days=holding_days,
        exit_reason=exit_reason,
        skip_reason="",
        lifecycle=lifecycle,
        result=result,
    )


__all__ = ["JobExecutor"]
