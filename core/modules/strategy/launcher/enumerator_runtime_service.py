#!/usr/bin/env python3
"""
枚举器 runtime：CLI / 工作台共用；含 universe 解析（原 ``stock_universe`` 合并入此文件）。

所在包 ``strategy.launcher`` 非 DbCache 职责域；说明见同包 ``__init__.py``。
"""

from __future__ import annotations

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
from .run_service import StrategyFingerprintManager
from core.utils.date.date_utils import DateUtils


def _stock_ids_for_enumerator_view(
    *,
    strategy_name: str,
    settings_view: StrategySettingsView,
    all_stocks: Optional[List[Dict[str, Any]]] = None,
    stock_count: Optional[int] = None,
) -> List[str]:
    """与枚举 run 一致的 ``stock_ids``；``stock_count`` 非空时与 workbench 连续窗采样覆盖一致。"""
    enum_settings = OpportunityEnumeratorSettings.from_base(settings_view)
    universe = all_stocks
    if universe is None:
        data_manager = DataManager(is_verbose=False)
        universe = data_manager.service.stock.list.load(filtered=True)

    # 股票池文件路径相对 ``userspace/strategies/<目录名>/``，须用发现名 strategy_name，非 settings.name 展示名
    if enum_settings.use_sampling:
        sampling_amount = stock_count if stock_count is not None else settings_view.sampling_amount
        sampling_config = (
            {"strategy": "continuous", "continuous": {"start_idx": 0}}
            if stock_count is not None
            else settings_view.sampling_config
        )
        return StockSamplingHelper.get_stock_list(
            all_stocks=universe,
            sampling_amount=sampling_amount,
            sampling_config=sampling_config,
            strategy_name=strategy_name,
        )

    return [s["id"] for s in universe]


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
    """CLI / 工作台共用的枚举 runtime 编排入口。"""

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
        force_refresh: bool = False,
    ) -> EnumeratorRuntimeContext:
        raw_settings = raw_settings_override if raw_settings_override is not None else strategy_info.settings.to_dict()
        settings_view = cls.build_canonical_settings(raw_settings)
        enum_settings = OpportunityEnumeratorSettings.from_base(settings_view)
        stock_list = _stock_ids_for_enumerator_view(
            strategy_name=strategy_name,
            settings_view=settings_view,
            all_stocks=None,
            stock_count=stock_count,
        )
        data_manager = DataManager(is_verbose=False)
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
            force_refresh=force_refresh,
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


__all__ = ["EnumeratorRuntimeContext", "EnumeratorRuntimeService"]
