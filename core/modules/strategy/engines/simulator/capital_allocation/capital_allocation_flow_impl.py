#!/usr/bin/env python3
"""Capital allocation flow implementation internals."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_settings_view,
)
from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
from core.modules.strategy.engines.simulator.helpers.enumerator_bootstrap import (
    resolve_or_build_enumerator_version,
)
from core.modules.strategy.services.data import StrategyDataOutputService
from core.modules.strategy.services.data.output import SimulationEvent, VersionManager
from .data_classes.account import Account
from .helpers.allocation import AllocationStrategy
from .helpers.fees import FeeCalculator
from .simulator import CapitalAllocationSimulator, CapitalAllocationSimulatorConfig

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class CapitalAllocationFlowImpl(CapitalAllocationSimulator):
    def load_settings(
        self, strategy_name: str, strategy_info: "DiscoveredStrategy | None"
    ):
        return load_strategy_settings_view(strategy_name, strategy_info=strategy_info)

    def parse_config(self, base_settings) -> CapitalAllocationSimulatorConfig:
        return CapitalAllocationSimulatorConfig.from_settings(base_settings)

    def resolve_source_version(
        self,
        *,
        strategy_name: str,
        base_settings,
        config: CapitalAllocationSimulatorConfig,
        strategy_info: "DiscoveredStrategy | None",
    ) -> Path:
        output_version_dir, _ = resolve_or_build_enumerator_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=config.use_sampling,
            base_version=config.base_version,
            strategy_info=strategy_info,
        )
        return output_version_dir

    def create_simulation_version(self, strategy_name: str):
        return VersionManager.create_capital_allocation_version(strategy_name)

    def create_profiler(self) -> PerformanceProfiler:
        profiler = PerformanceProfiler(stock_id="capital_allocation")
        profiler.start_timer("total")
        return profiler

    def load_event_stream(
        self,
        *,
        strategy_name: str,
        output_version_dir: Path,
        config: CapitalAllocationSimulatorConfig,
        profiler: PerformanceProfiler,
    ) -> List[SimulationEvent]:
        profiler.start_timer("load_data")
        data_loader = StrategyDataOutputService(
            strategy_name=strategy_name, cache_enabled=True
        )
        events = data_loader.build_event_stream(
            output_version_dir,
            start_date=config.start_date or "",
            end_date=config.end_date or "",
        )
        profiler.metrics.time_load_data = profiler.end_timer("load_data")
        profiler.metrics.opportunity_count = len(events)
        return events

    def create_execution_state(self, config: CapitalAllocationSimulatorConfig) -> Dict[str, Any]:
        account = Account(initial_cash=config.initial_capital, cash=config.initial_capital)
        fee_calculator = FeeCalculator(
            commission_rate=config.commission_rate,
            min_commission=config.min_commission,
            stamp_duty_rate=config.stamp_duty_rate,
            transfer_fee_rate=config.transfer_fee_rate,
        )
        allocation_strategy = AllocationStrategy(
            mode=config.allocation_mode,
            initial_capital=config.initial_capital,
            max_portfolio_size=config.max_portfolio_size,
            lot_size=config.lot_size,
            lots_per_trade=config.lots_per_trade,
            kelly_fraction=config.kelly_fraction,
            fee_calculator=fee_calculator,
        )
        return {
            "account": account,
            "fee_calculator": fee_calculator,
            "allocation_strategy": allocation_strategy,
            "trades": [],
            "equity_curve": [],
            "current_date": None,
            "completed_opportunities_map": {},
        }

    def replay_events(
        self,
        *,
        events: List[SimulationEvent],
        config: CapitalAllocationSimulatorConfig,
        state: Dict[str, Any],
        profiler: PerformanceProfiler,
    ) -> None:
        profiler.start_timer("enumerate")
        account = state["account"]
        allocation_strategy = state["allocation_strategy"]
        fee_calculator = state["fee_calculator"]
        for event in events:
            if event.date != state["current_date"]:
                if state["current_date"] is not None and config.save_equity_curve:
                    state["equity_curve"].append(
                        {
                            "date": state["current_date"],
                            "cash_balance": account.cash,
                            "total_equity": account.get_equity({}),
                            "open_positions": account.get_portfolio_size(),
                        }
                    )
                state["current_date"] = event.date

            if event.is_trigger():
                trade = self._handle_trigger_event(
                    event,
                    account,
                    allocation_strategy,
                    state["completed_opportunities_map"],
                )
                if trade:
                    state["trades"].append(trade)
            elif event.is_target():
                trade = self._handle_target_event(event, account, fee_calculator)
                if trade:
                    state["trades"].append(trade)
                    self._update_completed_opportunities(
                        event, state["completed_opportunities_map"], account
                    )
        profiler.metrics.time_enumerate = profiler.end_timer("enumerate")

    def finalize_equity_curve(
        self,
        *,
        config: CapitalAllocationSimulatorConfig,
        state: Dict[str, Any],
    ) -> None:
        if state["current_date"] is not None and config.save_equity_curve:
            account = state["account"]
            state["equity_curve"].append(
                {
                    "date": state["current_date"],
                    "cash_balance": account.cash,
                    "total_equity": account.get_equity({}),
                    "open_positions": account.get_portfolio_size(),
                }
            )

__all__ = ["CapitalAllocationFlowImpl", "CapitalAllocationSimulatorConfig"]
