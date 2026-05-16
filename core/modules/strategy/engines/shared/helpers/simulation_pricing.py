#!/usr/bin/env python3
"""由 ``StrategySimulationSettings`` 的枚举，从日线 K 线推导盯盘价与理论成交价（引擎内统一实现）。"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    MonitorPriceModel,
    NoNextBarPolicy,
    TradePriceModel,
)

Side = Literal["buy", "sell"]


def _f(k: Dict[str, Any], key: str) -> float:
    try:
        return float(k.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def monitor_bar_price(kline: Dict[str, Any], model: MonitorPriceModel) -> float:
    """持仓盯盘：本 bar 上用于与目标规则比较的一口价。"""
    if model == MonitorPriceModel.CLOSE:
        return _f(kline, "close")
    h, l, c = _f(kline, "high"), _f(kline, "low"), _f(kline, "close")
    if h and l:
        return (h + l) / 2.0
    return c


def trade_price_defers_to_next_session(model: TradePriceModel) -> bool:
    """``next_open``：信号日只记账 trigger，成交价在下一交易日 bar 上取 open。"""
    return model == TradePriceModel.NEXT_OPEN


def trade_theoretical_price_on_bar(
    model: TradePriceModel,
    *,
    side: Side,
    bar: Dict[str, Any],
) -> Optional[float]:
    """仅用当日 bar 取理论价（未加减滑点）。``NEXT_OPEN`` 在成交日等价于当日 open。"""
    if model == TradePriceModel.CLOSE:
        return _f(bar, "close")
    if model in (TradePriceModel.OPEN, TradePriceModel.NEXT_OPEN):
        return _f(bar, "open") or _f(bar, "close")
    if side == "buy":
        return _f(bar, "high") or _f(bar, "close")
    return _f(bar, "low") or _f(bar, "close")


def trade_theoretical_price(
    model: TradePriceModel,
    *,
    side: Side,
    bar: Dict[str, Any],
    next_bar: Optional[Dict[str, Any]] = None,
    no_next_bar: NoNextBarPolicy = "use_last_close",
) -> Optional[float]:
    """同日可成交模型；``next_open`` 请走延迟队列，勿传 ``next_bar``。"""
    if trade_price_defers_to_next_session(model):
        return apply_no_next_bar_buy_fallback_price(bar, no_next_bar=no_next_bar)
    return trade_theoretical_price_on_bar(model, side=side, bar=bar)


def apply_no_next_bar_buy_fallback_price(
    bar: Dict[str, Any],
    *,
    no_next_bar: NoNextBarPolicy,
) -> Optional[float]:
    if no_next_bar == "skip_trade":
        return None
    return _f(bar, "close")


def apply_buy_slippage(price: float, buy_bps: float) -> float:
    return float(price) * (1.0 + max(0.0, float(buy_bps)) / 10_000.0)


def apply_sell_slippage(price: float, sell_bps: float) -> float:
    return float(price) * (1.0 - max(0.0, float(sell_bps)) / 10_000.0)


__all__ = [
    "apply_buy_slippage",
    "apply_no_next_bar_buy_fallback_price",
    "apply_sell_slippage",
    "monitor_bar_price",
    "trade_price_defers_to_next_session",
    "trade_theoretical_price",
    "trade_theoretical_price_on_bar",
]
