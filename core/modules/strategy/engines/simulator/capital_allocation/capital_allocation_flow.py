#!/usr/bin/env python3
"""Capital allocation simulation flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from .capital_allocation_flow_impl import CapitalAllocationFlowImpl

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class CapitalAllocationFlow(BaseSimulationFlow):
    """Three-stage capital allocation simulation flow."""

    def __init__(self, is_verbose: bool = False) -> None:
        self._impl = CapitalAllocationFlowImpl(is_verbose=is_verbose)

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> Dict[str, Any]:
        # step1: read raw strategy settings
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        # step2: parse simulator-specific config from settings
        config = self._impl.parse_config(base_settings)
        # step3: resolve source data version and create simulation version
        output_version_dir = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            strategy_info=strategy_info,
        )
        sim_version_dir, sim_version_id = self._impl.create_simulation_version(
            strategy_name
        )
        # step4: initialize runtime profiling context
        profiler = self._impl.create_profiler()
        return {
            "strategy_name": strategy_name,
            "base_settings": base_settings,
            "config": config,
            "output_version_dir": output_version_dir,
            "sim_version_dir": sim_version_dir,
            "sim_version_id": sim_version_id,
            "profiler": profiler,
        }

    def execute(self, preprocessed: Dict[str, Any]) -> Dict[str, Any]:
        # step1: load ordered event stream from output artifacts
        events = self._impl.load_event_stream(
            strategy_name=preprocessed["strategy_name"],
            output_version_dir=preprocessed["output_version_dir"],
            config=preprocessed["config"],
            profiler=preprocessed["profiler"],
        )
        if not events:
            return {"empty": True}
        # step2: initialize account/funding/allocation execution state
        state = self._impl.create_execution_state(preprocessed["config"])
        # step3: replay trigger/target events into trades and positions
        self._impl.replay_events(
            events=events,
            config=preprocessed["config"],
            state=state,
            profiler=preprocessed["profiler"],
        )
        # step4: flush final day equity snapshot
        self._impl.finalize_equity_curve(config=preprocessed["config"], state=state)
        return {"events": events, **state}

    def postprocess(
        self, preprocessed: Dict[str, Any], executed: Dict[str, Any]
    ) -> Dict[str, Any]:
        # step1: aggregate metrics, persist outputs and run analyzer hooks
        return self._impl.postprocess(preprocessed, executed)


__all__ = ["CapitalAllocationFlow"]
