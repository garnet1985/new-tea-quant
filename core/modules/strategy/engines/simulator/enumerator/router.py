#!/usr/bin/env python3
"""按 simulation.execution_mode 选择枚举 flow。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.flow import (
    CalendarSlicedEnumeratorFlow,
)
from core.modules.strategy.engines.simulator.enumerator.shared.flow import (
    BaseEnumeratorFlow,
)
from core.modules.strategy.engines.simulator.enumerator.stock_based.flow import (
    StockBasedEnumeratorFlow,
)


def create_enumerator_flow(
    *,
    execution_mode: str,
    start_date: str,
    end_date: str,
    stock_list: List[str],
    max_workers: Union[str, int] = "auto",
    base_settings: Optional[StrategySettingsView] = None,
    workbench_strategy_name: Optional[str] = None,
    workbench_run_id: Optional[str] = None,
    force_refresh: bool = False,
    backtest_period: Optional[Dict[str, str]] = None,
) -> BaseEnumeratorFlow:
    kwargs = dict(
        start_date=start_date,
        end_date=end_date,
        stock_list=stock_list,
        max_workers=max_workers,
        base_settings=base_settings,
        workbench_strategy_name=workbench_strategy_name,
        workbench_run_id=workbench_run_id,
        force_refresh=force_refresh,
        backtest_period=backtest_period,
    )
    if str(execution_mode or "").strip() == "calendar_slice":
        return CalendarSlicedEnumeratorFlow(**kwargs)
    return StockBasedEnumeratorFlow(**kwargs)


__all__ = [
    "BaseEnumeratorFlow",
    "CalendarSlicedEnumeratorFlow",
    "StockBasedEnumeratorFlow",
    "create_enumerator_flow",
]
