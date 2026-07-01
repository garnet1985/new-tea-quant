"""entity_based DataContext 组装。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.shared.data_classes import Opportunity
from core.modules.strategy.core.hooks.context import DataContext


class EntityDataContext:
    """entity_based hook 数据 context 组装。"""

    @staticmethod
    def assemble_init(
        *,
        strategy_name: str,
        settings: StrategySettings,
        stock_list: List[str],
        entity_id: str,
        entity_info: Dict[str, Any],
        data: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> DataContext:
        return DataContext.assemble(
            strategy_name=strategy_name,
            settings=settings,
            stock_list=stock_list,
            entity_id=entity_id,
            entity_info=entity_info,
            data=data,
            extra=extra,
        )

    @staticmethod
    def assemble_scan(
        *,
        strategy_name: str,
        settings: StrategySettings,
        stock_list: List[str],
        entity_id: str,
        entity_info: Dict[str, Any],
        now: str,
        data: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
        opportunity: Optional[Opportunity] = None,
    ) -> DataContext:
        return DataContext.assemble(
            strategy_name=strategy_name,
            settings=settings,
            stock_list=stock_list,
            entity_id=entity_id,
            entity_info=entity_info,
            now=now,
            data=data,
            extra=extra,
            opportunity=opportunity,
        )


__all__ = ["EntityDataContext"]
