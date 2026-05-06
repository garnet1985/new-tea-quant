#!/usr/bin/env python3
"""
枚举 runtime 用的 **股票 universe** 解析（``EnumeratorRuntimeService.build_context``）。

默认 ``DataManager.service.stock.list.load(filtered=True)`` + ``StockSamplingHelper``；DbCache 指纹的 ``stock_ids`` 由调用方直接传入，不经此模块。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper
from core.modules.strategy.engines.simulator.enumerator import OpportunityEnumeratorSettings


def stock_ids_for_enumerator_view(
    *,
    strategy_name: str,
    settings_view: StrategySettingsView,
    all_stocks: Optional[List[Dict[str, Any]]] = None,
    stock_count: Optional[int] = None,
) -> List[str]:
    """
    由已有 ``StrategySettingsView`` 得到与枚举 run 一致的 ``stock_ids`` 列表。

    ``stock_count`` 非空时与 ``EnumeratorRuntimeService.build_context`` 的 workbench 覆盖行为一致
    （连续窗采样配置）。
    """
    enum_settings = OpportunityEnumeratorSettings.from_base(settings_view)
    universe = all_stocks
    if universe is None:
        data_manager = DataManager(is_verbose=False)
        universe = data_manager.service.stock.list.load(filtered=True)

    # pool/blacklist 等策略依赖策略名解析相对路径；空名回退到目录名，与指纹/env 解析一致。
    helper_strategy_name = str(settings_view.name or "").strip() or strategy_name

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
            strategy_name=helper_strategy_name,
        )

    return [s["id"] for s in universe]
