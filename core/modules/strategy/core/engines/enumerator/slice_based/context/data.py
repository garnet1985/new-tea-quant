"""slice_based DataContext 组装。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.shared.data_classes import Opportunity
from core.modules.strategy.core.hooks.context import DataContext


class SliceDataContext:
    """slice_based hook 数据 context 组装。"""

    @staticmethod
    def assemble_asof(
        *,
        strategy_name: str,
        settings: StrategySettings,
        stock_list: List[str],
        as_of: str,
        calendar: Dict[str, Any],
    ) -> DataContext:
        return DataContext.assemble(
            strategy_name=strategy_name,
            settings=settings,
            stock_list=stock_list,
            now=as_of,
            calendar=calendar,
        )

    @staticmethod
    def assemble_scan(
        *,
        strategy_name: str,
        settings: StrategySettings,
        stock_list: List[str],
        entity_id: str,
        entity_info: Dict[str, Any],
        as_of: str,
        data: Dict[str, Any],
        calendar: Dict[str, Any],
        opportunity: Optional[Opportunity] = None,
    ) -> DataContext:
        return DataContext.assemble(
            strategy_name=strategy_name,
            settings=settings,
            stock_list=stock_list,
            entity_id=entity_id,
            entity_info=entity_info,
            now=as_of,
            data=data,
            calendar=calendar,
            opportunity=opportunity,
        )


__all__ = ["SliceDataContext"]
