#!/usr/bin/env python3
"""v2：PIT 全市场 + 年度换仓横截面 demo。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.hooks import StrategyHooks, StrategyHookContext
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfResult,
)

_SHARED = Path(__file__).resolve().parents[1] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from calendar_period import (  # noqa: E402
    is_rebalance_period_end,
    is_rebalance_period_start,
    require_rebalance_period,
)
from selection import (  # noqa: E402
    INDICATORS,
    TAGS_SLOT,
    RebalanceFilters,
    find_bar_on_date,
    passes_cap_filter,
    passes_price_range,
)

__all__ = ["LowPricePitRebalanceHooks"]


class LowPricePitRebalanceHooks(StrategyHooks):
    """PIT 全市场：周期首个交易日横截面选股，末个交易日清仓。"""

    def on_calendar_asof(self, ctx: StrategyHookContext) -> CalendarAsOfResult:
        calendar = ctx.calendar
        if calendar is None:
            return CalendarAsOfResult(selected_stock_ids=[])
        settings = ctx.settings_dict()
        carry = dict(calendar.carry or {})
        period = require_rebalance_period(settings)

        if is_rebalance_period_end(calendar, period):
            carry["force_exit_open_date"] = calendar.as_of_date
            carry.pop("period_selected", None)
            return CalendarAsOfResult(selected_stock_ids=[], carry=carry)

        if not is_rebalance_period_start(calendar, period):
            return CalendarAsOfResult(selected_stock_ids=[], carry=carry)

        filters = RebalanceFilters.from_settings(settings)
        as_of_date = calendar.as_of_date

        candidates: List[Tuple[str, float]] = []
        for sid, stock_data in calendar.stocks.items():
            if not isinstance(stock_data, dict):
                continue
            sid_s = str(sid).strip()
            if not sid_s:
                continue

            klines = stock_data.get("klines")
            if not klines:
                continue
            bar = find_bar_on_date(klines, as_of_date)
            if bar is None:
                continue

            close = float(bar["close"])
            if not passes_price_range(close, filters.min_close, filters.max_close):
                continue

            indicators = stock_data.get(INDICATORS) or []
            tag_rows = stock_data.get(TAGS_SLOT) or []
            if not passes_cap_filter(
                filters=filters,
                as_of_date=as_of_date,
                indicators=indicators,
                tag_rows=tag_rows,
            ):
                continue

            candidates.append((sid_s, close))

        candidates.sort(key=lambda item: (item[1], item[0]))
        selected = [sid for sid, _ in candidates[: filters.top_n]]

        carry["period_selected"] = list(selected)
        carry.pop("force_exit_open_date", None)
        return CalendarAsOfResult(selected_stock_ids=selected, carry=carry)

    def scan_opportunity(self, ctx: StrategyHookContext) -> Optional[Opportunity]:
        data = ctx.scan.data if ctx.scan else {}
        settings = ctx.settings_dict()
        record_of_today = self.get_record_of_today(data)
        if record_of_today is None:
            return None

        close = float(record_of_today["close"])
        period = require_rebalance_period(settings)

        return self.build_opportunity(
            ctx,
            record_of_today,
            extra_fields={
                "close": close,
                "rebalance": period,
            },
        )
