#!/usr/bin/env python3
"""Per-stock worker for price factor simulation.

与历史 master 分支 ``PriceFactorSimulatorWorker`` 对齐：
- 按 ``trigger_date``、``opportunity_id`` 排序机会；
- 同一只股票在 **当前持仓未结束**（``trigger_date <= holding_until``）时 **不接受** 新机会；
- 使用 ``sell_date`` → ``exit_date`` → ``trigger_date`` 解析平仓日，与 master 的 ``InvestmentBuilder`` 约定一致。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
from core.modules.strategy.engines.shared.simulator_hooks_dispatcher import (
    SimulatorHooksDispatcher,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.investment import (
    PriceFactorInvestment,
)
from core.modules.strategy.engines.simulator.price_factor.helpers import DateTimeEncoder
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
        self.sim_version_dir = Path(job_payload["sim_version_dir"])
        self.config_dict: Dict[str, Any] = job_payload.get("config", {})
        self.hooks_dispatcher = SimulatorHooksDispatcher(self.strategy_name)
        self.profiler = PerformanceProfiler(self.stock_id)

    @staticmethod
    def execute_job(job_payload: Dict[str, Any]) -> Dict[str, Any]:
        return PriceFactorWorker(job_payload).run()

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
                "total_win": 0,
                "total_loss": 0,
                "total_open": 0,
                "total_profit": 0.0,
                "avg_roi": 0.0,
                "avg_duration_in_days": 0.0,
            }
        return {
            "total_investments": len(investments),
            "total_win": len([x for x in investments if x.get("status") == "win"]),
            "total_loss": len([x for x in investments if x.get("status") == "loss"]),
            "total_open": len([x for x in investments if x.get("status") == "open"]),
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

    def _simulate(self) -> Dict[str, Any]:
        cfg = self.config_dict or {}
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
                self.stock_id,
                stock_summary,
                cfg,
            )
            return modified or stock_summary

        self.hooks_dispatcher.call_hook(
            "on_price_factor_before_process_stock",
            self.stock_id,
            opportunities_rows,
            cfg,
        )

        self.profiler.start_timer("enumerate")
        order = sorted(
            range(len(opportunities_rows)),
            key=lambda i: (
                str(opportunities_rows[i].get("trigger_date") or ""),
                str(opportunities_rows[i].get("opportunity_id") or ""),
            ),
        )

        investments: List[Dict[str, Any]] = []
        holding_until: Optional[str] = None

        for idx in order:
            row = opportunities_rows[idx]
            hooked = self.hooks_dispatcher.call_hook(
                "on_price_factor_opportunity_trigger",
                dict(row),
                cfg,
            )
            modified_row = dict(hooked) if isinstance(hooked, dict) else dict(row)

            trigger_date = str(modified_row.get("trigger_date") or "").strip()
            buy_fill = parse_opportunity_buy_fill(modified_row)
            if buy_fill is None:
                continue
            buy_date, _buy_price = buy_fill
            sell_date = str(modified_row.get("sell_date") or "").strip()
            exit_from_row = str(modified_row.get("exit_date") or "").strip()
            resolved_exit = sell_date or exit_from_row or buy_date

            # 持仓未结束时若新机会买入日仍早于等于持仓结束日则跳过（``YYYYMMDD`` 字符串序）
            if holding_until is not None and buy_date and holding_until:
                if buy_date <= holding_until:
                    continue

            holding_until = resolved_exit or buy_date

            opp_id = str(modified_row.get("opportunity_id") or "").strip()
            merged = dict(modified_row)
            merged["exit_date"] = resolved_exit

            processed_targets: List[Dict[str, Any]] = []
            for t_idx in targets_index.get(opp_id) or []:
                if t_idx < 0 or t_idx >= len(targets_rows):
                    continue
                t_row = targets_rows[t_idx]
                modified_t = self.hooks_dispatcher.call_hook(
                    "on_price_factor_target_hit",
                    t_row,
                    merged,
                    cfg,
                )
                processed_targets.append(
                    dict(modified_t if isinstance(modified_t, dict) else t_row)
                )

            investment = PriceFactorInvestment.from_opportunity(
                merged,
                processed_targets,
                stock_name=str(modified_row.get("stock_name") or ""),
            ).to_dict()
            investments.append(investment)

        self.profiler.metrics.time_enumerate = self.profiler.end_timer("enumerate")

        stock_summary = {
            "stock": {"id": self.stock_id},
            "investments": investments,
            "summary": self._summary_from_investments(investments),
        }
        modified_summary = self.hooks_dispatcher.call_hook(
            "on_price_factor_after_process_stock",
            self.stock_id,
            stock_summary,
            cfg,
        )
        return modified_summary or stock_summary

    def _save_stock_json(self, stock_summary: Dict[str, Any]) -> None:
        from core.utils.io.csv_io import write_dicts_to_csv

        path_mgr = StrategyOutputPathService(sim_version_dir=self.sim_version_dir)
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


__all__ = ["PriceFactorWorker"]
