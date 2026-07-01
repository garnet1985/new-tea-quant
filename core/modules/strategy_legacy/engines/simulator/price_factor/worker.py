#!/usr/bin/env python3
"""Per-stock worker for price factor simulation.

- 按 ``buy_date``、``opportunity_id`` 排序；须具备有效 ``buy_date`` / ``buy_price``（枚举器产出）。
- 同股持仓未结束前（``buy_date <= holding_until``）跳过后续机会。
- ``holding_until`` 仅在价格层实际成交平仓后推进；卖出因跌停等被跳过时仓位仍为 open，锁至回测结束日。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from core.modules.market_profile import get_market_profile
from core.modules.strategy.engines.shared.helpers.market_profile_id import (
    resolve_market_profile_id,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)
from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
    ROW_SKIP_REASON_KEY,
    should_skip_investment,
)
from core.modules.strategy.engines.shared.helpers.tradability import (
    should_skip_buy,
    should_skip_sell,
)
from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
from core.modules.strategy.engines.shared.simulator_hooks_dispatcher import (
    SimulatorHooksDispatcher,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.investment import (
    PriceFactorInvestment,
)
from core.modules.strategy.engines.simulator.price_factor.helpers import (
    DateTimeEncoder,
    resolve_holding_until,
)
from core.modules.strategy.engines.simulator.price_factor.helpers.deferred_exit import (
    retry_deferred_exits,
)
from core.modules.strategy.engines.simulator.price_factor.helpers.holding import (
    position_fully_closed,
)
from core.modules.strategy.engines.simulator.price_factor.helpers.klines_loader import (
    load_stock_klines,
)
from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    InvestmentOutcome,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import load_strategy_settings_view
from core.modules.strategy.hooks import price_factor_context
from core.modules.strategy.services.data import StrategyOutputReaderService
from core.modules.strategy.services.data.output.event import parse_opportunity_buy_fill
from core.modules.strategy.services.data.output import StrategyOutputPathService


class PriceFactorWorker:
    def __init__(self, job_payload: Dict[str, Any]) -> None:
        self.job_payload = job_payload
        self.stock_id: str = job_payload["stock_id"]
        self.strategy_name: str = job_payload["strategy_name"]
        self.opportunities_path = Path(job_payload["opportunities_path"])
        self.targets_path = Path(job_payload["targets_path"])
        self.output_version_dir = Path(job_payload["output_version_dir"])
        self.config_dict: Dict[str, Any] = job_payload.get("config", {})
        self.hooks_dispatcher = SimulatorHooksDispatcher(self.strategy_name)
        self._settings_view: Optional[StrategySettingsView] = None
        self.profiler = PerformanceProfiler(self.stock_id)
        self._apply_skip_save(bool(job_payload.get("_bench_skip_save")))

    def _apply_skip_save(self, skip: bool) -> None:
        if skip:
            self._save_stock_json = lambda _summary: None  # type: ignore[method-assign]

    def run(self) -> Dict[str, Any]:
        self.profiler.start_timer("total")
        try:
            stock_summary = self._simulate()
            self._save_stock_json(stock_summary)
            self.profiler.metrics.time_total = self.profiler.end_timer("total")
            metrics = self.profiler.finalize()
            return {
                "success": True,
                "stock_id": self.stock_id,
                "stock": stock_summary["stock"],
                "investments": stock_summary["investments"],
                "summary": stock_summary["summary"],
                "performance_metrics": metrics.to_dict(),
            }
        except Exception as exc:
            self.profiler.metrics.time_total = self.profiler.end_timer("total")
            return {
                "success": False,
                "stock_id": self.stock_id,
                "error": str(exc),
                "performance_metrics": self.profiler.finalize().to_dict(),
            }

    def _summary_from_investments(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """单只股票聚合 summary（供 ``PriceReport.from_stock_summaries`` 跨股票加权）。"""
        if not investments:
            return {
                "total_investments": 0,
                "total_complete_win": 0,
                "total_complete_loss": 0,
                "total_open": 0,
                "total_profit": 0.0,
                "avg_roi": 0.0,
                "avg_duration_in_days": 0.0,
            }
        return {
            "total_investments": len(investments),
            "total_complete_win": len([
                x for x in investments
                if x.get("lifecycle") == InvestmentLifecycle.COMPLETE.value
                and x.get("outcome") == InvestmentOutcome.WIN.value
            ]),
            "total_complete_loss": len([
                x for x in investments
                if x.get("lifecycle") == InvestmentLifecycle.COMPLETE.value
                and x.get("outcome") == InvestmentOutcome.LOSS.value
            ]),
            "total_open": len([
                x for x in investments if x.get("lifecycle") == InvestmentLifecycle.OPEN.value
            ]),
            "total_profit": sum(float(x.get("profit", 0.0) or 0.0) for x in investments),
            "avg_roi": (
                sum(float(x.get("roi", 0.0) or 0.0) for x in investments) / len(investments)
                if investments
                else 0.0
            ),
            "avg_duration_in_days": (
                sum(float(x.get("holding_days", 0) or 0.0) for x in investments)
                / len(investments)
                if investments
                else 0.0
            ),
        }

    def _settings_view_for_hooks(self) -> StrategySettingsView:
        if self._settings_view is not None:
            return self._settings_view
        try:
            self._settings_view = load_strategy_settings_view(self.strategy_name)
        except Exception:
            self._settings_view = StrategySettingsView.from_dict(self.config_dict or {})
        return self._settings_view

    def _pf_hook_ctx(self, **kwargs):
        return price_factor_context(
            strategy_name=self.strategy_name,
            settings=self._settings_view_for_hooks(),
            stock_id=self.stock_id,
            config=self.config_dict or {},
            **kwargs,
        )

    def _simulate(self) -> Dict[str, Any]:
        cfg = self.config_dict or {}
        sim_settings = StrategySimulationSettings.from_strategy_root(cfg)
        profile_id = resolve_market_profile_id(self.job_payload)
        if not str(self.job_payload.get("market_profile_id") or "").strip():
            raise ValueError(
                "price_factor job 缺少 market_profile_id（应由 PriceFactorFlow.execute 注入）"
            )
        market_profile = get_market_profile(profile_id)
        self.profiler.start_timer("load_data")
        data_loader = StrategyOutputReaderService(
            strategy_name=self.strategy_name, cache_enabled=False
        )
        opportunities_rows, targets_rows, targets_index = data_loader.load_rows_for_stock(
            opportunities_path=self.opportunities_path,
            targets_path=self.targets_path,
            start_date=self.config_dict.get("start_date") or "",
            end_date=self.config_dict.get("end_date") or "",
        )
        self.profiler.metrics.time_load_data = self.profiler.end_timer("load_data")
        self.profiler.metrics.opportunity_count = len(opportunities_rows)
        self.profiler.metrics.target_count = len(targets_rows)

        if not opportunities_rows:
            stock_summary = {
                "stock": {"id": self.stock_id},
                "investments": [],
                "summary": self._summary_from_investments([]),
            }
            modified = self.hooks_dispatcher.call_hook(
                "on_price_factor_after_process_stock",
                self._pf_hook_ctx(stock_summary=stock_summary),
            )
            return modified or stock_summary

        self.hooks_dispatcher.call_hook(
            "on_price_factor_before_process_stock",
            self._pf_hook_ctx(opportunities=opportunities_rows),
        )

        self.profiler.start_timer("enumerate")
        order = sorted(
            range(len(opportunities_rows)),
            key=lambda i: (
                str(opportunities_rows[i].get("buy_date") or ""),
                str(opportunities_rows[i].get("opportunity_id") or ""),
            ),
        )

        investments: List[Dict[str, Any]] = []
        holding_until: Optional[str] = None
        skipped_buy_at_limit_up = 0
        skipped_sell_at_limit_down = 0
        skipped_stock_status = 0
        backtest_end_date = str(self.config_dict.get("end_date") or "").strip()

        for idx in order:
            row = opportunities_rows[idx]
            hooked = self.hooks_dispatcher.call_hook(
                "on_price_factor_opportunity_trigger",
                self._pf_hook_ctx(opportunity_row=dict(row)),
            )
            modified_row = dict(hooked) if isinstance(hooked, dict) else dict(row)

            skip_reason = should_skip_investment(
                modified_row,
                sim_settings.skip_investment_when,
            )
            if skip_reason:
                modified_row[ROW_SKIP_REASON_KEY] = skip_reason
                skipped_stock_status += 1
                continue

            buy_fill = parse_opportunity_buy_fill(modified_row)
            if buy_fill is None:
                continue
            buy_date, buy_price = buy_fill
            if should_skip_buy(
                modified_row,
                market_profile,
                self.stock_id,
                buy_price,
                allow_at_limit=sim_settings.allow_buy_at_limit_up,
            ):
                skipped_buy_at_limit_up += 1
                continue
            # 持仓未结束时若新机会买入日仍早于等于持仓结束日则跳过（``YYYYMMDD`` 字符串序）
            if holding_until is not None and buy_date and holding_until:
                if buy_date <= holding_until:
                    continue

            opp_id = str(modified_row.get("opportunity_id") or "").strip()
            merged = dict(modified_row)

            processed_targets: List[Dict[str, Any]] = []
            skipped_targets: List[Dict[str, Any]] = []
            for t_idx in targets_index.get(opp_id) or []:
                if t_idx < 0 or t_idx >= len(targets_rows):
                    continue
                t_row = targets_rows[t_idx]
                modified_t = self.hooks_dispatcher.call_hook(
                    "on_price_factor_target_hit",
                    self._pf_hook_ctx(
                        target_row=t_row,
                        opportunity_row=merged,
                    ),
                )
                target_dict = dict(modified_t if isinstance(modified_t, dict) else t_row)
                raw_sell = (
                    target_dict.get("sell_price")
                    or target_dict.get("price")
                    or target_dict.get("target_price")
                    or 0.0
                )
                try:
                    sell_px = float(raw_sell or 0.0)
                except (TypeError, ValueError):
                    sell_px = 0.0
                if should_skip_sell(
                    target_dict,
                    market_profile,
                    self.stock_id,
                    sell_px,
                    allow_at_limit=sim_settings.allow_sell_at_limit_down,
                ):
                    skipped_sell_at_limit_down += 1
                    skipped_targets.append(target_dict)
                    continue
                processed_targets.append(target_dict)

            pending_exit = None
            if skipped_targets and not position_fully_closed(processed_targets):
                klines = load_stock_klines(
                    self.stock_id,
                    start_date=buy_date,
                    end_date=backtest_end_date or buy_date,
                )
                processed_targets, pending_exit, defer_skips = retry_deferred_exits(
                    buy_price=buy_price,
                    processed_targets=processed_targets,
                    skipped_targets=skipped_targets,
                    klines=klines,
                    sim_settings=sim_settings,
                    market_profile=market_profile,
                    stock_id=self.stock_id,
                    allow_sell_at_limit=sim_settings.allow_sell_at_limit_down,
                )
                skipped_sell_at_limit_down += defer_skips

            holding_until = resolve_holding_until(
                processed_targets=processed_targets,
                buy_date=buy_date,
                backtest_end_date=backtest_end_date,
            )

            investment = PriceFactorInvestment.from_opportunity(
                merged,
                processed_targets,
                stock_name=str(modified_row.get("stock_name") or ""),
                goal_config=self.config_dict.get("goal"),
                backtest_calendar=self.config_dict.get("backtest_calendar"),
                backtest_end_date=backtest_end_date,
                pending_exit=pending_exit,
            ).to_dict()
            investments.append(investment)

        self.profiler.metrics.time_enumerate = self.profiler.end_timer("enumerate")

        stock_summary = {
            "stock": {"id": self.stock_id},
            "investments": investments,
            "summary": self._summary_from_investments(investments),
            "skipped_buy_at_limit_up": skipped_buy_at_limit_up,
            "skipped_sell_at_limit_down": skipped_sell_at_limit_down,
            "skipped_stock_status": skipped_stock_status,
        }
        modified_summary = self.hooks_dispatcher.call_hook(
            "on_price_factor_after_process_stock",
            self._pf_hook_ctx(stock_summary=stock_summary),
        )
        return modified_summary or stock_summary

    def _save_stock_json(self, stock_summary: Dict[str, Any]) -> None:
        from core.utils.io.csv_io import write_dicts_to_csv

        path_mgr = StrategyOutputPathService(output_version_dir=self.output_version_dir)
        stock_path = path_mgr.stock_json_path(self.stock_id)
        self.profiler.start_timer("save_csv")
        before = stock_path.stat().st_size if stock_path.exists() else 0
        with stock_path.open("w", encoding="utf-8") as f:
            json.dump(stock_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        after = stock_path.stat().st_size if stock_path.exists() else 0
        elapsed = self.profiler.end_timer("save_csv")
        self.profiler.metrics.time_save_csv += elapsed
        self.profiler.record_file_write(max(0, after - before), elapsed)
        investments = stock_summary.get("investments") or []
        if investments:
            write_dicts_to_csv(stock_path.with_suffix(".csv"), investments)


def run_price_factor_payload(
    job_payload: Dict[str, Any],
    *,
    in_subprocess: bool = True,
) -> Dict[str, Any]:
    """执行 price dispatch job（``stock_jobs`` 内顺序多股，一次 bootstrap）。"""
    import multiprocessing as mp

    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    stock_jobs = job_payload.get("stock_jobs")
    if not isinstance(stock_jobs, list) or not stock_jobs:
        raise ValueError("price dispatch job 缺少非空 stock_jobs")

    rows = [dict(j) for j in stock_jobs if isinstance(j, dict)]
    if not rows:
        return {"success": False, "bulk": True, "stock_results": [], "error": "empty stock_jobs"}

    skip_save = bool(job_payload.get("_bench_skip_save"))
    if skip_save:
        for row in rows:
            row["_bench_skip_save"] = True

    use_sub = in_subprocess and mp.current_process().name != "MainProcess"
    if use_sub:
        bootstrap_strategy_worker_data_manager()
    stock_results: List[Dict[str, Any]] = []
    try:
        for sub in rows:
            try:
                worker = PriceFactorWorker(sub)
                stock_results.append(worker.run())
            except Exception as exc:
                sid = str(sub.get("stock_id") or "")
                stock_results.append(
                    {
                        "success": False,
                        "stock_id": sid,
                        "error": str(exc),
                    }
                )
    finally:
        if use_sub:
            release_strategy_worker_runtime()

    ids = [str(r.get("stock_id") or "") for r in stock_results if r.get("stock_id")]
    return {
        "success": all(bool(r.get("success")) for r in stock_results),
        "bulk": True,
        "stock_results": stock_results,
        "stock_ids": ids or [str(r.get("stock_id") or "") for r in rows],
    }


__all__ = ["PriceFactorWorker", "run_price_factor_payload"]
