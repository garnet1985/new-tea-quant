#!/usr/bin/env python3
"""Unified enumerator runtime facade for CLI and BFF."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper
from core.modules.strategy.engines.simulator.enumerator import (
    OpportunityEnumeratorFlow,
    OpportunityEnumeratorSettings,
)
from core.modules.strategy.services.fingerprint import (
    StrategyFingerprintManager,
    StrategyFingerprintRuntimeService,
)
from core.modules.strategy.strategy_manager import StrategyManager
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)


@dataclass
class EnumeratorRuntimeContext:
    strategy_name: str
    strategy_info: Any
    settings_view: StrategySettingsView
    enum_settings: OpportunityEnumeratorSettings
    stock_list: List[str]
    start_date: str
    end_date: str
    flow: OpportunityEnumeratorFlow


class EnumeratorRuntimeService:
    """Single owner for canonical enumerate runtime/fingerprint/snapshot orchestration."""

    @staticmethod
    def build_canonical_settings(raw_settings: Dict[str, Any]) -> StrategySettingsView:
        return StrategySettingsView.from_dict(
            StrategyFingerprintManager.canonicalize_settings(raw_settings)
        )

    @classmethod
    def build_context(
        cls,
        *,
        strategy_name: str,
        strategy_info: Any,
        raw_settings_override: Optional[Dict[str, Any]] = None,
        stock_count: Optional[int] = None,
        workbench_run_id: Optional[str] = None,
        workbench_strategy_name: Optional[str] = None,
    ) -> EnumeratorRuntimeContext:
        raw_settings = raw_settings_override if raw_settings_override is not None else strategy_info.settings.to_dict()
        settings_view = cls.build_canonical_settings(raw_settings)
        enum_settings = OpportunityEnumeratorSettings.from_base(settings_view)
        data_manager = DataManager(is_verbose=False)
        all_stocks = data_manager.service.stock.list.load(filtered=True)
        if enum_settings.use_sampling:
            sampling_amount = stock_count if stock_count is not None else settings_view.sampling_amount
            sampling_config = (
                {"strategy": "continuous", "continuous": {"start_idx": 0}}
                if stock_count is not None
                else settings_view.sampling_config
            )
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=sampling_amount,
                sampling_config=sampling_config,
                strategy_name=settings_view.name,
            )
        else:
            stock_list = [s["id"] for s in all_stocks]
        latest_date = data_manager.service.calendar.get_latest_completed_trading_date()
        start_date = settings_view.start_date or DateUtils.DEFAULT_START_DATE
        end_date = settings_view.end_date or latest_date
        flow = OpportunityEnumeratorFlow(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=enum_settings.max_workers,
            base_settings=settings_view,
            workbench_strategy_name=workbench_strategy_name,
            workbench_run_id=workbench_run_id,
        )
        return EnumeratorRuntimeContext(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            settings_view=settings_view,
            enum_settings=enum_settings,
            stock_list=stock_list,
            start_date=start_date,
            end_date=end_date,
            flow=flow,
        )

    @staticmethod
    def run_enum(context: EnumeratorRuntimeContext) -> List[Dict[str, Any]]:
        return context.flow.run(
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
        )

    @staticmethod
    def build_fingerprints(context: EnumeratorRuntimeContext) -> tuple[str, str]:
        return StrategyFingerprintRuntimeService.build_ids_for_runtime_context(context)

    @staticmethod
    def preprocess(context: EnumeratorRuntimeContext) -> Any:
        return context.flow.preprocess(
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
        )

    @staticmethod
    def build_ids_from_preprocessed(preprocessed: Any) -> tuple[str, str]:
        request_fp = getattr(preprocessed, "request_fingerprint", None)
        return StrategyFingerprintRuntimeService.build_ids_from_request_fingerprint(request_fp)


__all__ = ["EnumeratorRuntimeContext", "EnumeratorRuntimeService"]
