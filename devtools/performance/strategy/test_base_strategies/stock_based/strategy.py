#!/usr/bin/env python3
"""RSI 超卖 + 财报基本面准入演示策略（entity_based enumerate smoke）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.modules.data_contract.contracts import DataKey
from core.modules.strategy.contracts import DataContext, Opportunity, StrategyHooks
from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig

logger = logging.getLogger(__name__)

_FINANCE_SLOT = StrategyDataConfig.storage_key_for(DataKey.STOCK_CORPORATE_FINANCE)


class RsiFundamentalGateHooks(StrategyHooks):
    """
    RSI(14) 超卖触发；最新已披露季度 ``netprofit_yoy`` 不低于阈值才入场。

    财报 PIT 由 ``stock.finance.quarterly`` contract 的 ``ann_date`` 时间轴 +
    ``DataCursor.until(signal_date)`` 保证，策略只消费 cursor 前缀的最后一行。
    """

    def scan_opportunity(self, ctx: DataContext) -> Optional[Opportunity]:
        data = ctx.data.to_dict()
        settings = ctx.effective_settings_dict()
        record_of_today = self.get_record_of_today(data, base_data_key=ctx.base_data_key)
        if record_of_today is None or not self._has_rsi_warmup(data, settings):
            return None

        rsi_value = self._rsi_value(record_of_today, settings)
        if rsi_value is None or not self._is_oversold(rsi_value, settings):
            return None

        finance_rows = data.get(_FINANCE_SLOT) or []
        if not finance_rows:
            return None
        finance_row = finance_rows[-1]

        netprofit_yoy = finance_row.get("netprofit_yoy")
        if netprofit_yoy is None:
            return None
        try:
            netprofit_yoy_value = float(netprofit_yoy)
        except (TypeError, ValueError):
            return None
        if netprofit_yoy_value < self._min_netprofit_yoy(settings):
            return None

        return self.build_opportunity(
            ctx,
            record_of_today,
            extra_fields={
                "rsi_value": rsi_value,
                "finance_quarter": finance_row.get("quarter"),
                "finance_ann_date": finance_row.get("ann_date"),
                "netprofit_yoy": netprofit_yoy_value,
            },
        )

    def _has_rsi_warmup(self, data: Dict[str, Any], settings: Dict[str, Any]) -> bool:
        rsi_length = int(settings["data"]["base"]["indicators"]["rsi"][0]["length"])
        base_key = str(settings["data"]["base"]["data_key"])
        rows = data.get(base_key) or []
        return len(rows) >= rsi_length

    def _rsi_value(
        self, record_of_today: Dict[str, Any], settings: Dict[str, Any]
    ) -> Optional[float]:
        rsi_length = int(settings["data"]["base"]["indicators"]["rsi"][0]["length"])
        raw = record_of_today.get(f"rsi{rsi_length}")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _is_oversold(self, rsi_value: float, settings: Dict[str, Any]) -> bool:
        threshold = float(settings["core"]["rsi_oversold_threshold"])
        return rsi_value < threshold

    @staticmethod
    def _min_netprofit_yoy(settings: Dict[str, Any]) -> float:
        core = settings.get("core") or {}
        if "min_netprofit_yoy" not in core:
            return 0.0
        return float(core["min_netprofit_yoy"])
