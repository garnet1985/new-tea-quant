#!/usr/bin/env python3
"""Per-stock worker for price factor simulation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
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

    def _simulate(self) -> Dict[str, Any]:
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
        self.profiler.start_timer("enumerate")
        investments: List[Dict[str, Any]] = []
        for row in opportunities_rows:
            opp_id = str(row.get("opportunity_id") or "").strip()
            matched_targets = [
                targets_rows[i]
                for i in (targets_index.get(opp_id) or [])
                if 0 <= i < len(targets_rows)
            ]
            investment = PriceFactorInvestment.from_opportunity(
                row,
                matched_targets,
                stock_name=str(row.get("stock_name", "")),
            ).to_dict()
            investments.append(investment)
        self.profiler.metrics.time_enumerate = self.profiler.end_timer("enumerate")
        return {
            "stock": {"id": self.stock_id},
            "investments": investments,
            "summary": {
                "total_investments": len(investments),
                "total_win": len(
                    [item for item in investments if item.get("status") == "win"]
                ),
                "total_loss": len(
                    [item for item in investments if item.get("status") == "loss"]
                ),
                "total_open": len(
                    [item for item in investments if item.get("status") == "open"]
                ),
                "total_profit": sum(
                    float(item.get("profit", 0.0) or 0.0) for item in investments
                ),
                "avg_roi": (
                    sum(float(item.get("roi", 0.0) or 0.0) for item in investments)
                    / len(investments)
                    if investments
                    else 0.0
                ),
                "avg_duration_in_days": (
                    sum(
                        float(item.get("holding_days", 0) or 0.0)
                        for item in investments
                    )
                    / len(investments)
                    if investments
                    else 0.0
                ),
            },
        }

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
