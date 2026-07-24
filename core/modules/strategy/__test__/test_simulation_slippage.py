"""slippage + edges.no_next_tick 接线（Investment 成交）。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.shared.data_class import (
    Investment,
    InvestmentRunDeps,
    Lifecycle,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity, StockInfo
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    SlippageConfig,
    StrategySettings,
)


OPEN_DATES = ("20240102", "20240103", "20240104")


def _bar(date: str, *, o: float, h: float, l: float, c: float) -> dict:
    return {"date": date, "open": o, "high": h, "low": l, "close": c}


def _tick(date: str, *, o: float, h: float, l: float, c: float):
    return date, _bar(date, o=o, h=h, l=l, c=c)


def _react(inv: Investment, tick) -> bool:
    as_of, bar = tick
    if inv.lifecycle == Lifecycle.COMPLETE:
        return False
    if inv.lifecycle == Lifecycle.PENDING_TO_ENTER:
        inv.try_enter(as_of, bar)
    elif inv.lifecycle == Lifecycle.PENDING_TO_EXIT:
        inv.try_exit(as_of, bar)
    elif inv.lifecycle == Lifecycle.OPEN:
        inv.check_targets(as_of, bar)
    return inv.lifecycle != Lifecycle.COMPLETE


def _settings(**tradability) -> StrategySettings:
    raw = {
        "simulation": {
            "execution": {
                "mode": "entity_based",
                "steps": [
                    "check_settlement",
                    "check_stop_loss",
                    "check_take_profit",
                    "check_expiration",
                ],
            },
            "assumption": {
                "template": "none",
                "tradability": {
                    "enter_price": "next_open",
                    "exit_price": "close",
                    **tradability,
                },
            },
            "risk_control": {},
        },
        "goal": {
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        },
    }
    settings = StrategySettings(raw_settings=raw)
    settings.apply_defaults()
    return settings


def _inv(settings: StrategySettings, *, trigger: str = "20240102", close: float = 10.0) -> Investment:
    opp = Opportunity(
        stock=StockInfo(id="600000.SH"),
        record_of_today=_bar(trigger, o=close, h=close + 1, l=close - 1, c=close),
        trigger_date=trigger,
        trigger_price=close,
    )
    opp.market_profile = "china_a_stock"
    return Investment.create_from_opportunity(
        opp, settings=settings, open_dates=OPEN_DATES
    )


class TestSlippageConfig(unittest.TestCase):
    def test_apply_enter_exit_bps(self) -> None:
        slip = SlippageConfig(enter_bps=10.0, exit_bps=10.0)
        self.assertAlmostEqual(slip.apply_enter(100.0), 100.1)
        self.assertAlmostEqual(slip.apply_exit(100.0), 99.9)


class TestInvestmentSlippage(unittest.TestCase):
    def test_enter_and_exit_apply_slippage(self) -> None:
        settings = _settings(
            slippage={"enter_bps": 100.0, "exit_bps": 100.0},  # 1%
            enter_price="close",
            exit_price="close",
        )
        # close enter on trigger day
        settings.raw_settings["simulation"]["assumption"]["tradability"]["enter_price"] = "close"
        settings.apply_defaults()

        inv = _inv(settings, close=10.0)
        # enter at trigger close 10 → 10.1
        self.assertTrue(_react(inv, _tick("20240102", o=10, h=11, l=9, c=10)))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertAlmostEqual(inv.entry.entry_price, 10.1)

        # T+1 then stop via expiration? use settle for clean exit
        _react(inv, _tick("20240103", o=10, h=11, l=9, c=10))
        self.assertFalse(inv.settle(*_tick("20240104", o=10, h=11, l=9, c=12)))
        # exit close 12 → 12 * 0.99 = 11.88
        self.assertAlmostEqual(inv.exit_info.exit_price, 11.88)

    def test_run_deps_reads_slippage_and_no_next_tick(self) -> None:
        settings = _settings(
            slippage={"enter_bps": 5.0, "exit_bps": 7.0},
            edges={"no_next_tick": "use_last_close"},
        )
        deps = InvestmentRunDeps.from_settings(
            settings=settings,
            market_rules=object(),
            open_dates=OPEN_DATES,
        )
        self.assertEqual(deps.slippage.enter_bps, 5.0)
        self.assertEqual(deps.slippage.exit_bps, 7.0)
        self.assertEqual(deps.no_next_tick, "use_last_close")


class TestNoNextTick(unittest.TestCase):
    def test_skip_trade_abandons_pending_enter(self) -> None:
        settings = _settings(edges={"no_next_tick": "skip_trade"})
        inv = _inv(settings)
        self.assertEqual(inv.lifecycle, Lifecycle.PENDING_TO_ENTER)
        # 无下一交易日 open → settle 放弃
        self.assertFalse(inv.settle(*_tick("20240102", o=10, h=11, l=9, c=10)))
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertEqual(inv.entry.entry_price, 0.0)
        self.assertFalse(inv.exit_info.exit_date)

    def test_use_last_close_fills_then_settles(self) -> None:
        settings = _settings(
            edges={"no_next_tick": "use_last_close"},
            slippage={"enter_bps": 100.0, "exit_bps": 0.0},
        )
        inv = _inv(settings, close=10.0)
        # 信号日 close=10，进场 10.1；再用 settle bar close=12 出场
        self.assertFalse(inv.settle(*_tick("20240108", o=11, h=12, l=10, c=12)))
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertAlmostEqual(inv.entry.entry_price, 10.1)
        self.assertEqual(inv.entry.entry_date, "20240102")
        self.assertAlmostEqual(inv.exit_info.exit_price, 12.0)
        self.assertEqual(inv.exit_info.exit_reason, "simulate_end")


if __name__ == "__main__":
    unittest.main()
