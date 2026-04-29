#!/usr/bin/env python3
"""Price factor flow implementation internals."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_settings_view,
)
from core.modules.strategy.engines.shared.performance_profiler import (
    AggregateProfiler,
    PerformanceMetrics,
)
from core.modules.strategy.engines.simulator.helpers.enumerator_bootstrap import (
    resolve_or_build_enumerator_version,
)
from core.modules.strategy.engines.simulator.price_factor.simulator import (
    PriceFactorSimulator,
    PriceFactorSimulatorConfig,
    PriceFactorSimulatorWorker,
)
from core.modules.strategy.services.data.output import VersionManager

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class PriceFactorFlowImpl(PriceFactorSimulator):
    def load_settings(
        self, strategy_name: str, strategy_info: "DiscoveredStrategy | None"
    ):
        return load_strategy_settings_view(strategy_name, strategy_info=strategy_info)

    def parse_config(self, base_settings) -> PriceFactorSimulatorConfig:
        return self._build_config_from_settings(base_settings)

    def resolve_source_version(
        self,
        *,
        strategy_name: str,
        base_settings,
        config: PriceFactorSimulatorConfig,
        strategy_info: "DiscoveredStrategy | None",
    ):
        return resolve_or_build_enumerator_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=config.use_sampling,
            base_version=config.base_version,
            strategy_info=strategy_info,
        )

    def scan_stock_files(self, output_version_dir: Path) -> Dict[str, Dict[str, Path]]:
        return self._scan_output_files(output_version_dir)

    def create_simulation_version(self, strategy_name: str):
        return VersionManager.create_price_factor_version(strategy_name)

    def build_worker_jobs(
        self,
        *,
        strategy_name: str,
        sim_version_dir: Path,
        stock_files: Dict[str, Dict[str, Path]],
        config: PriceFactorSimulatorConfig,
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
                    "config": config.__dict__,
                }
            )
        return jobs

    def run_worker_jobs(
        self,
        *,
        jobs: List[Dict[str, Any]],
        max_workers: "str | int",
    ) -> List[Dict[str, Any]]:
        from core.infra.worker.multi_process.process_worker import (
            ExecutionMode as ProcessExecutionMode,
        )
        from core.infra.worker.multi_process.process_worker import JobStatus, ProcessWorker

        if not jobs:
            return []
        worker_pool = ProcessWorker(
            max_workers=ProcessWorker.resolve_max_workers(
                max_workers, module_name="PriceFactorSimulator"
            ),
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=PriceFactorSimulatorWorker.execute_job,
            is_verbose=self.is_verbose,
        )
        process_jobs = [{"id": job["stock_id"], "payload": job} for job in jobs]
        worker_pool.run_jobs(process_jobs)
        results: List[Dict[str, Any]] = []
        for jr in worker_pool.get_results():
            if jr.status == JobStatus.COMPLETED:
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

__all__ = [
    "PriceFactorFlowImpl",
    "PriceFactorSimulatorConfig",
    "PriceFactorSimulatorWorker",
]
