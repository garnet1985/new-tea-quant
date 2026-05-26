#!/usr/bin/env python3
"""Ensure enumerator output version is ready for simulators."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
    backtest_period_to_dict,
    resolve_backtest_universe,
    resolve_latest_completed_trading_date,
)
from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper
from core.modules.strategy.services.data.output import StrategyOutputVersionService

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class StrategyEnumeratorBootstrapService:
    @staticmethod
    def resolve_or_build_enumerator_version(
        *,
        strategy_name: str,
        base_settings: StrategySettingsView,
        use_sampling: bool,
        base_version: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
    ) -> Tuple[Path, Path]:
        raw_version = (base_version or "latest").strip()
        if "/" in raw_version:
            raw_version = raw_version.split("/", 1)[1].strip() or "latest"
        version_spec = raw_version
        try:
            return StrategyOutputVersionService.resolve_enumerator_version(
                strategy_name, version_spec
            )
        except FileNotFoundError:
            if raw_version != "latest":
                try:
                    return StrategyOutputVersionService.resolve_enumerator_version(
                        strategy_name, "latest"
                    )
                except FileNotFoundError:
                    pass

        resolved_dir = StrategyEnumeratorBootstrapService.run_enumerator_for_mode(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=use_sampling,
            strategy_info=strategy_info,
        )
        if resolved_dir is not None:
            return resolved_dir, resolved_dir.parent
        return StrategyOutputVersionService.resolve_enumerator_version(
            strategy_name, "latest"
        )

    @staticmethod
    def run_enumerator_for_mode(
        *,
        strategy_name: str,
        base_settings: StrategySettingsView,
        use_sampling: bool,
        strategy_info: Optional["DiscoveredStrategy"] = None,
    ) -> Optional[Path]:
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.simulator.enumerator import (
            OpportunityEnumeratorFlow,
        )
        data_mgr = DataManager(is_verbose=False)
        list_svc = data_mgr.service.stock.list
        period, universe = resolve_backtest_universe(
            list_svc=list_svc,
            settings_view=base_settings,
            latest_completed_trading_date=resolve_latest_completed_trading_date(data_mgr),
            data_manager=data_mgr,
        )
        if use_sampling:
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=universe,
                sampling_amount=base_settings.sampling_amount or len(universe),
                sampling_config=base_settings.sampling_config or {},
                strategy_name=strategy_name,
            )
        else:
            stock_list = [stock["id"] for stock in universe if stock.get("id")]
        flow = OpportunityEnumeratorFlow(
            start_date=period.start_date,
            end_date=period.end_date,
            stock_list=stock_list,
            max_workers="auto",
            base_settings=base_settings,
            backtest_period=backtest_period_to_dict(period),
        )
        result = flow.run(strategy_name=strategy_name, strategy_info=strategy_info)
        if result and isinstance(result, list):
            first = result[0] or {}
            version_dir_name = str(first.get("version_dir", "")).strip()
            if version_dir_name:
                version_dir, _ = StrategyOutputVersionService.resolve_enumerator_version(
                    strategy_name,
                    version_dir_name,
                )
                return version_dir
        return None


__all__ = ["StrategyEnumeratorBootstrapService"]
