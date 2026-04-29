#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import json
import logging
import time

from core.modules.strategy.engines.analyzer import Analyzer
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
    DiscoveredStrategy,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_settings_view,
)
from core.modules.strategy.engines.shared.simulator_hooks_dispatcher import SimulatorHooksDispatcher
from core.modules.strategy.engines.shared.performance_profiler import (
    AggregateProfiler,
    PerformanceMetrics,
    PerformanceProfiler,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.investment import (
    PriceFactorInvestment,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.report import PriceReport
from core.modules.strategy.engines.simulator.price_factor.helpers import DateTimeEncoder
from core.modules.strategy.engines.simulator.helpers.enumerator_bootstrap import (
    resolve_or_build_enumerator_version,
)
from core.modules.strategy.services.data import StrategyDataOutputService
from core.modules.strategy.services.data.output import ResultPathManager, VersionManager

logger = logging.getLogger(__name__)


@dataclass
class PriceFactorSimulatorConfig:
    base_version: str = "latest"
    use_sampling: bool = True
    start_date: str = ""
    end_date: str = ""
    commission_rate: float = 0.0
    min_commission: float = 0.0
    stamp_duty_rate: float = 0.0
    transfer_fee_rate: float = 0.0
    max_workers: "str | int" = "auto"


class PriceFactorSimulator:
    def __init__(self, is_verbose: bool = False) -> None:
        self.is_verbose = is_verbose

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional[DiscoveredStrategy] = None,
    ) -> Dict[str, Any]:
        base_settings = load_strategy_settings_view(
            strategy_name, strategy_info=strategy_info
        )
        simulator_config = self._build_config_from_settings(base_settings)
        output_version_dir, output_root = resolve_or_build_enumerator_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=simulator_config.use_sampling,
            base_version=simulator_config.base_version,
            strategy_info=strategy_info,
        )
        sim_version_dir, sim_version_id = VersionManager.create_price_factor_version(strategy_name)
        data_loader = StrategyDataOutputService(
            strategy_name=strategy_name, cache_enabled=True
        )
        stock_files = self._scan_output_files(output_version_dir)
        if not stock_files:
            return {}

        from core.infra.worker.multi_process.process_worker import ExecutionMode as ProcessExecutionMode
        from core.infra.worker.multi_process.process_worker import JobStatus, ProcessWorker

        jobs: List[Dict[str, Any]] = []
        for stock_id, paths in stock_files.items():
            jobs.append(
                {
                    "stock_id": stock_id,
                    "strategy_name": strategy_name,
                    "sim_version_dir": str(sim_version_dir),
                    "opportunities_path": str(paths["opportunities"]),
                    "targets_path": str(paths["targets"]),
                    "config": simulator_config.__dict__,
                }
            )
        worker_pool = ProcessWorker(
            max_workers=ProcessWorker.resolve_max_workers(simulator_config.max_workers, module_name="PriceFactorSimulator"),
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=PriceFactorSimulatorWorker.execute_job,
            is_verbose=self.is_verbose,
        )
        process_jobs = [{"id": job["stock_id"], "payload": job} for job in jobs]
        aggregate_profiler = AggregateProfiler()
        worker_pool.run_jobs(process_jobs)
        results: List[Dict[str, Any]] = []
        for jr in worker_pool.get_results():
            if jr.status == JobStatus.COMPLETED:
                results.append(jr.result or {})
        stock_summaries: List[Dict[str, Any]] = []
        for r in results:
            if r.get("success", False):
                stock_summaries.append(r)
                perf_data = r.get("performance_metrics")
                stock_id = r.get("stock_id")
                if perf_data and stock_id:
                    metrics = PerformanceMetrics.from_dict(perf_data)
                    aggregate_profiler.add_stock_metrics(str(stock_id), metrics)

        if not stock_summaries:
            return {}
        report = PriceReport.from_stock_summaries(stock_summaries)
        session_summary = report.to_dict()
        session_summary["output_version"] = {"version_dir": output_version_dir.name, "output_root": str(output_root.name)}
        session_summary["sim_version"] = {"version_id": sim_version_id, "version_dir": sim_version_dir.name}
        self._save_results(
            strategy_name=strategy_name,
            sim_version_dir=sim_version_dir,
            sim_version_id=sim_version_id,
            output_version_dir=output_version_dir,
            session_summary=session_summary,
            settings_snapshot=base_settings.to_dict(),
        )
        perf_summary = aggregate_profiler.get_summary()
        if perf_summary:
            with (sim_version_dir / "0_performance_report.json").open("w", encoding="utf-8") as f:
                json.dump(perf_summary, f, indent=2, ensure_ascii=False)
        try:
            Analyzer.run_for_simulator(
                strategy_name=strategy_name,
                sim_type="price_factor",
                sim_version_dir=sim_version_dir,
                raw_settings=base_settings.to_dict(),
            )
        except Exception:
            pass
        return session_summary

    def _build_config_from_settings(self, settings: StrategySettingsView) -> PriceFactorSimulatorConfig:
        settings_dict = settings.to_dict()
        simulator_cfg = settings_dict.get("price_simulator", {}) or {}
        fees_cfg = simulator_cfg.get("fees", {}) or {}
        return PriceFactorSimulatorConfig(
            base_version=simulator_cfg.get("base_version") or "latest",
            use_sampling=bool(simulator_cfg.get("use_sampling", True)),
            start_date=simulator_cfg.get("start_date", "") or "",
            end_date=simulator_cfg.get("end_date", "") or "",
            commission_rate=float(fees_cfg.get("commission_rate", 0.0) or 0.0),
            min_commission=float(fees_cfg.get("min_commission", 0.0) or 0.0),
            stamp_duty_rate=float(fees_cfg.get("stamp_duty_rate", 0.0) or 0.0),
            transfer_fee_rate=float(fees_cfg.get("transfer_fee_rate", 0.0) or 0.0),
            max_workers=simulator_cfg.get("max_workers", "auto"),
        )

    def _scan_output_files(self, version_dir: Path) -> Dict[str, Dict[str, Path]]:
        stock_files: Dict[str, Dict[str, Path]] = defaultdict(dict)
        for entry in version_dir.iterdir():
            if not entry.is_file():
                continue
            name = entry.name
            if name.endswith("_opportunities.csv"):
                stock_id = name[: -len("_opportunities.csv")]
                stock_files[stock_id]["opportunities"] = entry
            elif name.endswith("_targets.csv"):
                stock_id = name[: -len("_targets.csv")]
                stock_files[stock_id]["targets"] = entry
        return {s: p for s, p in stock_files.items() if "opportunities" in p and "targets" in p}

    def _save_results(
        self,
        strategy_name: str,
        sim_version_dir: Path,
        sim_version_id: int,
        output_version_dir: Path,
        session_summary: Dict[str, Any],
        settings_snapshot: Dict[str, Any],
    ) -> None:
        path_mgr = ResultPathManager(sim_version_dir=sim_version_dir)
        with path_mgr.session_summary_path().open("w", encoding="utf-8") as f:
            json.dump(session_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        metadata = {
            "strategy_name": strategy_name,
            "sim_version_id": sim_version_id,
            "sim_version_dir": sim_version_dir.name,
            "created_at": datetime.now().isoformat(),
            "output_version": {"version_dir": output_version_dir.name, "output_root": str(output_version_dir.parent.name)},
            "session_summary": session_summary,
            "settings_snapshot": settings_snapshot,
        }
        with path_mgr.metadata_path().open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)


class PriceFactorSimulatorWorker:
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
        return PriceFactorSimulatorWorker(job_payload).run()

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
            return {"success": False, "stock_id": self.stock_id, "error": str(exc), "performance_metrics": self.profiler.finalize().to_dict()}

    def _simulate(self) -> Dict[str, Any]:
        self.profiler.start_timer("load_data")
        data_loader = StrategyDataOutputService(
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
            matched_targets = [targets_rows[i] for i in (targets_index.get(opp_id) or []) if 0 <= i < len(targets_rows)]
            inv = PriceFactorInvestment.from_opportunity(
                row,
                matched_targets,
                stock_name=str(row.get("stock_name", "")),
            ).to_dict()
            investments.append(inv)
        self.profiler.metrics.time_enumerate = self.profiler.end_timer("enumerate")
        stock_summary = {
            "stock": {"id": self.stock_id},
            "investments": investments,
            "summary": {
                "total_investments": len(investments),
                "total_win": len([i for i in investments if i.get("status") == "win"]),
                "total_loss": len([i for i in investments if i.get("status") == "loss"]),
                "total_open": len([i for i in investments if i.get("status") == "open"]),
                "total_profit": sum(float(i.get("profit", 0.0) or 0.0) for i in investments),
                "avg_roi": (
                    sum(float(i.get("roi", 0.0) or 0.0) for i in investments) / len(investments)
                    if investments
                    else 0.0
                ),
                "avg_duration_in_days": (
                    sum(float(i.get("holding_days", 0) or 0.0) for i in investments) / len(investments)
                    if investments
                    else 0.0
                ),
            },
        }
        return stock_summary

    def _save_stock_json(self, stock_summary: Dict[str, Any]) -> None:
        from core.utils.io.csv_io import write_dicts_to_csv

        path_mgr = ResultPathManager(sim_version_dir=self.sim_version_dir)
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


__all__ = ["PriceFactorSimulatorConfig", "PriceFactorSimulator", "PriceFactorSimulatorWorker"]
