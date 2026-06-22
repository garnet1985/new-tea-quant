#!/usr/bin/env python3
"""v2：PIT 全市场 + 年度换仓横截面 demo。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
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

__all__ = ["LowPricePitRebalanceWorker"]


class LowPricePitRebalanceWorker(BaseStrategyWorker):
    """PIT 全市场：周期首个交易日横截面选股，末个交易日清仓。"""

    def on_calendar_asof(
        self,
        ctx: CalendarAsOfContext,
        settings: Dict[str, Any],
    ) -> CalendarAsOfResult:
        carry = dict(ctx.carry or {})
        period = require_rebalance_period(settings)

        # 1. 周期末：标记强制平仓，本日不进入 scan
        if is_rebalance_period_end(ctx, period):
            carry["force_exit_open_date"] = ctx.as_of_date
            carry.pop("period_selected", None)
            return CalendarAsOfResult(selected_stock_ids=[], carry=carry)

        # 2. 非周期首：本日不扫描
        if not is_rebalance_period_start(ctx, period):
            return CalendarAsOfResult(selected_stock_ids=[], carry=carry)

        # 3. 从 settings 解析横截面筛选条件（缺字段即报错）
        filters = RebalanceFilters.from_settings(settings)
        as_of_date = ctx.as_of_date

        # 4. 逐股过滤：as_of 日 K 线 → 价格带 → 市值 / Tag
        candidates: List[Tuple[str, float]] = []
        for sid, stock_data in ctx.stocks.items():
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

        # 5. 按收盘价从低到高排序，取 top_n
        candidates.sort(key=lambda item: (item[1], item[0]))
        selected = [sid for sid, _ in candidates[: filters.top_n]]

        carry["period_selected"] = list(selected)
        carry.pop("force_exit_open_date", None)
        return CalendarAsOfResult(selected_stock_ids=selected, carry=carry)

    def scan_opportunity(
        self,
        data: Dict[str, Any],
        settings: Dict[str, Any],
    ) -> Optional[Opportunity]:
        # 1. 取 as_of 日 K 线
        record_of_today = self.get_record_of_today(data)
        if record_of_today is None:
            return None

        # 2. 读取收盘价（缺字段即报错）
        close = float(record_of_today["close"])
        period = require_rebalance_period(settings)

        # 3. 组装买入机会
        return self.build_opportunity(
            record_of_today,
            extra_fields={
                "close": close,
                "rebalance": period,
            },
        )
