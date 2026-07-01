#!/usr/bin/env python3
"""PIT 全市场 + 年度换仓 slice_based 演示策略。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_contract.contracts import DataKey
from core.modules.strategy.contracts import CalendarAsOfResult, DataContext, Opportunity, StrategyHooks

_SHARED = Path(__file__).resolve().parents[1] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from calendar_period import (  # noqa: E402
    is_rebalance_period_end,
    is_rebalance_period_start,
    require_rebalance_period,
)
from selection import (  # noqa: E402
    RebalanceFilters,
    find_bar_on_date,
    passes_cap_filter,
    passes_price_range,
)

__all__ = ["LowPricePitRebalanceHooks"]


class LowPricePitRebalanceHooks(StrategyHooks):
    """PIT 全市场：周期首个交易日 slice 选股，末个交易日清仓。"""

    def on_calendar_asof(self, ctx: DataContext) -> CalendarAsOfResult:
        calendar = ctx.calendar
        if not calendar:
            return CalendarAsOfResult(as_of_date=str(ctx.get("now") or ""), stocks=[])

        settings = ctx.effective_settings_dict()
        # session_state：一次 enumerate run 内跨开市日持久化的策略状态
        session_state = dict(calendar.get("session_state") or {})
        period = require_rebalance_period(settings)
        as_of_date = str(calendar.get("as_of_date") or ctx.get("now") or "")

        if is_rebalance_period_end(calendar, period):
            session_state["force_exit_open_date"] = as_of_date
            session_state.pop("period_selected", None)
            return CalendarAsOfResult(
                as_of_date=as_of_date,
                stocks=[],
                session_state=session_state,
            )

        if not is_rebalance_period_start(calendar, period):
            return CalendarAsOfResult(
                as_of_date=as_of_date,
                stocks=[],
                session_state=session_state,
            )

        filters = RebalanceFilters.from_settings(settings)
        stocks_map = calendar.get("stocks") or {}
        if not isinstance(stocks_map, dict):
            stocks_map = {}

        candidates: List[Tuple[str, float]] = []
        for sid, stock_data in stocks_map.items():
            if not isinstance(stock_data, dict):
                continue
            sid_s = str(sid).strip()
            if not sid_s:
                continue

            base_rows = stock_data.get(ctx.base_data_key)
            if not base_rows:
                continue
            bar = find_bar_on_date(base_rows, as_of_date)
            if bar is None:
                continue

            close = float(bar["close"])
            if not passes_price_range(close, filters.min_close, filters.max_close):
                continue

            indicators = stock_data.get("indicators") or []
            tag_rows = stock_data.get(DataKey.TAG.value) or []
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

        session_state["period_selected"] = list(selected)
        session_state.pop("force_exit_open_date", None)
        return CalendarAsOfResult(
            as_of_date=as_of_date,
            stocks=selected,
            session_state=session_state,
        )

    def scan_opportunity(self, ctx: DataContext) -> Optional[Opportunity]:
        data = ctx.data.to_dict()
        settings = ctx.effective_settings_dict()
        record_of_today = self.get_record_of_today(data, base_data_key=ctx.base_data_key)
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
