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
            base_settings=preprocessed.base_settings,
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
        if executed.empty:
            return {}
        # step1: aggregate execution data into strategy-level summary
        summary = self._impl.build_summary(
            account=executed.account,
            trades=executed.trades or [],
            equity_curve=executed.equity_curve or [],
            initial_capital=preprocessed.config.initial_capital,
            events=executed.events or [],
            completed_opportunities_map=executed.completed_opportunities_map or {},
        )
        # step2: persist output artifacts and metadata
        preprocessed.profiler.start_timer("save_csv")
        self._impl.save_outputs(
            sim_version_dir=preprocessed.sim_version_dir,
            sim_version_id=preprocessed.sim_version_id,
            output_version=preprocessed.output_version_dir.name,
            trades=executed.trades or [],
            equity_curve=executed.equity_curve or [],
            summary=summary,
            config=preprocessed.config,
            settings_snapshot=preprocessed.base_settings.to_dict(),
        )
        preprocessed.profiler.metrics.time_save_csv = preprocessed.profiler.end_timer(
            "save_csv"
        )
        preprocessed.profiler.metrics.time_total = preprocessed.profiler.end_timer(
            "total"
        )
        # step3: persist performance report
        self._impl.save_performance_report(
            sim_version_dir=preprocessed.sim_version_dir,
            profiler=preprocessed.profiler,
        )
        # step4: trigger analyzer hooks
        self._impl.run_analyzer_hook(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            raw_settings=preprocessed.base_settings.to_dict(),
        )
        return summary


__all__ = ["CapitalAllocationFlow"]
