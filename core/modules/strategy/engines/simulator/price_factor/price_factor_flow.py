#!/usr/bin/env python3
"""Price factor simulation flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from .price_factor_flow_impl import PriceFactorFlowImpl

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class PriceFactorFlow(BaseSimulationFlow):
    """Three-stage price factor simulation flow."""

    def __init__(self, is_verbose: bool = False) -> None:
        self._impl = PriceFactorFlowImpl(is_verbose=is_verbose)

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> Dict[str, Any]:
        # step1: read raw strategy settings
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        # step2: parse simulator-specific config
        simulator_config = self._impl.parse_config(base_settings)
        # step3: resolve source output version and create simulation version
        output_version_dir, output_root = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=simulator_config,
            strategy_info=strategy_info,
        )
        sim_version_dir, sim_version_id = self._impl.create_simulation_version(
            strategy_name
        )
        # step4: discover per-stock input artifacts
        stock_files = self._impl.scan_stock_files(output_version_dir)
        return {
            "strategy_name": strategy_name,
            "base_settings": base_settings,
            "simulator_config": simulator_config,
            "output_version_dir": output_version_dir,
            "output_root": output_root,
            "sim_version_dir": sim_version_dir,
            "sim_version_id": sim_version_id,
            "stock_files": stock_files,
        }

    def execute(self, preprocessed: Dict[str, Any]) -> Dict[str, Any]:
        # step1: build process jobs per stock
        jobs = self._impl.build_worker_jobs(
            strategy_name=preprocessed["strategy_name"],
            sim_version_dir=preprocessed["sim_version_dir"],
            stock_files=preprocessed["stock_files"],
            config=preprocessed["simulator_config"],
        )
        # step2: run worker backend and collect raw worker outputs
        results = self._impl.run_worker_jobs(
            jobs=jobs, max_workers=preprocessed["simulator_config"].max_workers
        )
        # step3: extract successful stock summaries and aggregate profiler
        return self._impl.collect_stock_summaries(results)

    def postprocess(
        self, preprocessed: Dict[str, Any], executed: Dict[str, Any]
    ) -> Dict[str, Any]:
        # step1: aggregate report + persist artifacts + run analyzer hooks
        return self._impl.postprocess(preprocessed, executed)


__all__ = ["PriceFactorFlow"]
