#!/usr/bin/env python3
"""Ensure enumerator output version is ready for simulators."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
    DiscoveredStrategy,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper
from core.modules.strategy.engines.simulator.enumerator import OpportunityEnumeratorFlow
from core.modules.strategy.services.data.output import StrategyOutputVersionService


class StrategyEnumeratorBootstrapService:
    @staticmethod
    def resolve_or_build_enumerator_version(
        *,
        strategy_name: str,
        base_settings: StrategySettingsView,
        use_sampling: bool,
        base_version: str,
        strategy_info: Optional[DiscoveredStrategy] = None,
    ) -> Tuple[Path, Path]:
        sub_dir = "test" if use_sampling else "output"
        raw_version = (base_version or "latest").strip()
        if "/" in raw_version:
            raw_version = raw_version.split("/", 1)[1].strip() or "latest"
        version_spec = f"{sub_dir}/{raw_version}"
        try:
            return StrategyOutputVersionService.resolve_enumerator_version(
                strategy_name, version_spec
            )
        except FileNotFoundError:
            if raw_version != "latest":
                try:
                    return StrategyOutputVersionService.resolve_enumerator_version(
                        strategy_name, f"{sub_dir}/latest"
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
            strategy_name, f"{sub_dir}/latest"
        )

    @staticmethod
    def run_enumerator_for_mode(
        *,
        strategy_name: str,
        base_settings: StrategySettingsView,
        use_sampling: bool,
        strategy_info: Optional[DiscoveredStrategy] = None,
    ) -> Optional[Path]:
        from core.modules.data_manager import DataManager
        from core.utils.date.date_utils import DateUtils

        data_mgr = DataManager(is_verbose=False)
        all_stocks = data_mgr.service.stock.list.load(filtered=True)
        if use_sampling:
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=base_settings.sampling_amount or len(all_stocks),
                sampling_config=base_settings.sampling_config or {},
                strategy_name=strategy_name,
            )
        else:
            stock_list = [stock["id"] for stock in all_stocks]

        flow = OpportunityEnumeratorFlow(
            start_date=DateUtils.DEFAULT_START_DATE,
            end_date=data_mgr.service.calendar.get_latest_completed_trading_date(),
            stock_list=stock_list,
            max_workers="auto",
            base_settings=base_settings,
        )
        result = flow.run(strategy_name=strategy_name, strategy_info=strategy_info)
        if result and isinstance(result, list):
            first = result[0] or {}
            version_dir_name = str(first.get("version_dir", "")).strip()
            if version_dir_name:
                sub_dir_name = "test" if use_sampling else "output"
                version_dir, _ = StrategyOutputVersionService.resolve_enumerator_version(
                    strategy_name,
                    f"{sub_dir_name}/{version_dir_name}",
                )
                return version_dir
        return None


__all__ = ["StrategyEnumeratorBootstrapService"]
