#!/usr/bin/env python3
"""Price factor flow implementation internals."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List
import json

from core.modules.strategy.engines.analyzer import Analyzer
from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_settings_view,
)
from core.modules.strategy.engines.shared.performance_profiler import (
    AggregateProfiler,
    PerformanceMetrics,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.report import PriceReport
from core.modules.strategy.engines.simulator.price_factor.data_classes.settings import (
    StrategyPriceSimulatorSettings,
)
from core.modules.strategy.engines.simulator.price_factor.helpers import DateTimeEncoder
from core.modules.strategy.services.data import StrategyEnumeratorBootstrapService
from core.modules.strategy.services.data.output import (
    StrategyOutputPathService,
    StrategyOutputVersionService,
)
from .worker import PriceFactorWorker

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class PriceFactorFlowImpl:
    def __init__(self, is_verbose: bool = False) -> None:
        self.is_verbose = is_verbose

    def load_settings(
        self, strategy_name: str, strategy_info: "DiscoveredStrategy | None"
    ):
        return load_strategy_settings_view(strategy_name, strategy_info=strategy_info)

    def parse_config(
        self, base_settings
    ) -> StrategyPriceSimulatorSettings:
        config = StrategyPriceSimulatorSettings.from_strategy_root(
            base_settings.to_dict()
        )
        config.apply_defaults()
        return config

    def resolve_source_version(
        self,
        *,
        strategy_name: str,
        base_settings,
        config: StrategyPriceSimulatorSettings,
        strategy_info: "DiscoveredStrategy | None",
    ):
        return StrategyEnumeratorBootstrapService.resolve_or_build_enumerator_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=config.use_sampling,
            base_version=config.base_version,
            strategy_info=strategy_info,
        )

    def scan_stock_files(self, output_version_dir: Path) -> Dict[str, Dict[str, Path]]:
        return self._scan_output_files(output_version_dir)

    def create_simulation_version(self, strategy_name: str):
        return StrategyOutputVersionService.create_price_factor_version(strategy_name)

    def build_worker_jobs(
        self,
        *,
        strategy_name: str,
        sim_version_dir: Path,
        stock_files: Dict[str, Dict[str, Path]],
        config: StrategyPriceSimulatorSettings,
    ) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        for stock_id, paths in stock_files.items():
            jobs.append(
                {
                    "stock_id": stock_id,
                    "strategy_name": strategy_name,
                    "sim_version_dir": str(sim_version_dir),
                    "opportunities_path": str(paths["opportunities"]),
                    "targets_path": str(paths["targets"]),
                    "config": config.to_dict(),
                }
            )
        return jobs

    def run_worker_jobs(
        self,
        *,
        jobs: List[Dict[str, Any]],
        max_workers: "str | int",
    ) -> List[Dict[str, Any]]:
        from core.infra.worker import (
            ProcessExecutionMode,
            ProcessJobStatus,
            ProcessWorker,
        )

        if not jobs:
            return []
        worker_pool = ProcessWorker(
            max_workers=ProcessWorker.resolve_max_workers(
                max_workers, module_name="PriceFactorSimulator"
            ),
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=PriceFactorWorker.execute_job,
            is_verbose=self.is_verbose,
        )
        process_jobs = [{"id": job["stock_id"], "payload": job} for job in jobs]
        worker_pool.run_jobs(process_jobs)
        results: List[Dict[str, Any]] = []
        for jr in worker_pool.get_results():
            if jr.status == ProcessJobStatus.COMPLETED:
                results.append(jr.result or {})
        return results

    def collect_stock_summaries(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        stock_summaries: List[Dict[str, Any]] = []
        aggregate_profiler = AggregateProfiler()
        for result in results:
            if result.get("success", False):
                stock_summaries.append(result)
                perf_data = result.get("performance_metrics")
                stock_id = result.get("stock_id")
                if perf_data and stock_id:
                    metrics = PerformanceMetrics.from_dict(perf_data)
                    aggregate_profiler.add_stock_metrics(str(stock_id), metrics)
        return {
            "stock_summaries": stock_summaries,
            "aggregate_profiler": aggregate_profiler,
        }

    def build_session_summary(
        self,
        *,
        stock_summaries: List[Dict[str, Any]],
        output_version_dir: Path,
        output_root: Path,
        sim_version_dir: Path,
        sim_version_id: int,
    ) -> Dict[str, Any]:
        if not stock_summaries:
            return {}

        report = PriceReport.from_stock_summaries(stock_summaries)
        session_summary = report.to_dict()
        session_summary["output_version"] = {
            "version_dir": output_version_dir.name,
            "output_root": str(output_root.name),
        }
        session_summary["sim_version"] = {
            "version_id": sim_version_id,
            "version_dir": sim_version_dir.name,
        }
        return session_summary

    def save_session_outputs(
        self,
        *,
        strategy_name: str,
        sim_version_dir: Path,
        sim_version_id: int,
        output_version_dir: Path,
        session_summary: Dict[str, Any],
        settings_snapshot: Dict[str, Any],
    ) -> None:
        self._save_results(
            strategy_name=strategy_name,
            sim_version_dir=sim_version_dir,
            sim_version_id=sim_version_id,
            output_version_dir=output_version_dir,
            session_summary=session_summary,
            settings_snapshot=settings_snapshot,
        )

    def save_performance_report(
        self, *, sim_version_dir: Path, aggregate_profiler: AggregateProfiler
    ) -> None:
        perf_summary = aggregate_profiler.get_summary()
        if perf_summary:
            with (sim_version_dir / "0_performance_report.json").open(
                "w", encoding="utf-8"
            ) as f:
                json.dump(perf_summary, f, indent=2, ensure_ascii=False)

    def run_analyzer_hook(
        self, *, strategy_name: str, sim_version_dir: Path, raw_settings: Dict[str, Any]
    ) -> None:
        try:
            Analyzer.run_for_simulator(
                strategy_name=strategy_name,
                sim_type="price_factor",
                sim_version_dir=sim_version_dir,
                raw_settings=raw_settings,
            )
        except Exception:
            pass

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
        return {
            stock_id: paths
            for stock_id, paths in stock_files.items()
            if "opportunities" in paths and "targets" in paths
        }

    def _save_results(
        self,
        strategy_name: str,
        sim_version_dir: Path,
        sim_version_id: int,
        output_version_dir: Path,
        session_summary: Dict[str, Any],
        settings_snapshot: Dict[str, Any],
    ) -> None:
        path_mgr = StrategyOutputPathService(sim_version_dir=sim_version_dir)
        with path_mgr.session_summary_path().open("w", encoding="utf-8") as f:
            json.dump(
                session_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder
            )
        metadata = {
            "strategy_name": strategy_name,
            "sim_version_id": sim_version_id,
            "sim_version_dir": sim_version_dir.name,
            "created_at": datetime.now().isoformat(),
            "output_version": {
                "version_dir": output_version_dir.name,
                "output_root": str(output_version_dir.parent.name),
            },
            "session_summary": session_summary,
            "settings_snapshot": settings_snapshot,
        }
        with path_mgr.metadata_path().open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)


__all__ = [
    "PriceFactorFlowImpl",
]
