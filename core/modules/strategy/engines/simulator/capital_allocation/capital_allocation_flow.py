#!/usr/bin/env python3
"""Capital allocation simulation flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.flow_context import (
    CapitalAllocationExecuteContext,
    CapitalAllocationPreprocessContext,
)
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
    ) -> CapitalAllocationPreprocessContext:
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
        return CapitalAllocationPreprocessContext(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            output_version_dir=output_version_dir,
            sim_version_dir=sim_version_dir,
            sim_version_id=sim_version_id,
            profiler=profiler,
        )

    def execute(
        self, preprocessed: CapitalAllocationPreprocessContext
    ) -> CapitalAllocationExecuteContext:
        # step1: load ordered event stream from output artifacts
        events = self._impl.load_event_stream(
            strategy_name=preprocessed.strategy_name,
            output_version_dir=preprocessed.output_version_dir,
            config=preprocessed.config,
            profiler=preprocessed.profiler,
        )
        if not events:
            return CapitalAllocationExecuteContext(empty=True)
        # step2: initialize account/funding/allocation execution state
        state = self._impl.create_execution_state(preprocessed.config)
        # step3: replay trigger/target events into trades and positions
        self._impl.replay_events(
            events=events,
            config=preprocessed.config,
            state=state,
            profiler=preprocessed.profiler,
        )
        # step4: flush final day equity snapshot
        self._impl.finalize_equity_curve(config=preprocessed.config, state=state)
        return CapitalAllocationExecuteContext(
            empty=False,
            events=events,
            account=state["account"],
            trades=state["trades"],
            equity_curve=state["equity_curve"],
            completed_opportunities_map=state["completed_opportunities_map"],
        )

    def postprocess(
        self,
        preprocessed: CapitalAllocationPreprocessContext,
        executed: CapitalAllocationExecuteContext,
    ) -> Dict[str, object]:
        # step1: aggregate metrics, persist outputs and run analyzer hooks
        preprocessed_payload = {
            "strategy_name": preprocessed.strategy_name,
            "base_settings": preprocessed.base_settings,
            "config": preprocessed.config,
            "output_version_dir": preprocessed.output_version_dir,
            "sim_version_dir": preprocessed.sim_version_dir,
            "sim_version_id": preprocessed.sim_version_id,
            "profiler": preprocessed.profiler,
        }
        executed_payload = {
            "empty": executed.empty,
            "events": executed.events,
            "account": executed.account,
            "trades": executed.trades,
            "equity_curve": executed.equity_curve,
            "completed_opportunities_map": executed.completed_opportunities_map,
        }
        return self._impl.postprocess(preprocessed_payload, executed_payload)


__all__ = ["CapitalAllocationFlow"]
