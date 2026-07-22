#!/usr/bin/env python3
"""Investment.tick 单元测试。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.engines.shared.data_class import (
    Investment,
    InvestmentRunDeps,
    InvestmentTickInput,
    Lifecycle,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity, StockInfo
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


OPEN_DATES = ("20240102", "20240103", "20240104", "20240105", "20240108")


def _bar(
    date: str,
    *,
    o: float,
    h: float,
    l: float,
    c: float,
    raw: dict | None = None,
) -> dict:
    row = {"date": date, "open": o, "high": h, "low": l, "close": c}
    if raw is not None:
        row["raw"] = raw
    return row


def _tick(
    date: str,
    *,
    o: float,
    h: float,
    l: float,
    c: float,
    raw: dict | None = None,
) -> InvestmentTickInput:
    return InvestmentTickInput(
        as_of_date=date,
        bar=_bar(date, o=o, h=h, l=l, c=c, raw=raw),
        data_as_of=date,
    )



def _settings(**overrides) -> StrategySettings:
    raw = {
        "simulation": {
            "buy_price_model": "next_open",
            "sell_price_model": "close",
            "execute_steps": [
                "check_settlement",
                "check_stop_loss",
                "check_take_profit",
                "check_expiration",
            ],
        },
        "goal": {
            "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
            "take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]},
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        },
    }
    raw.update(overrides)
    settings = StrategySettings(raw_settings=raw)
    settings.apply_defaults()
    return settings


def _inv(opp: Opportunity, settings: StrategySettings) -> Investment:
    opp.market_profile = "china_a_stock"
    return Investment.create_from_opportunity(
        opp,
        settings=settings,
        open_dates=OPEN_DATES,
    )


class TestInvestmentFromOpportunity(unittest.TestCase):
    def test_from_opportunity_copies_signal_fields(self) -> None:
        opp = Opportunity(
            stock=StockInfo(id="600000.SH", name="浦发银行"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, _settings())
        self.assertEqual(inv.trigger_date, "20240102")
        self.assertEqual(inv.trigger_price, 10.0)
        self.assertEqual(inv.lifecycle, Lifecycle.PENDING_TO_ENTER)
        self.assertEqual(inv.holding.window_days, 30)
        self.assertIsInstance(inv.run_deps, InvestmentRunDeps)


class TestInvestmentTick(unittest.TestCase):
    def test_next_open_entry_and_t_plus_one_settlement_gate(self) -> None:
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)

        self.assertTrue(inv.tick(_tick("20240103", o=10.5, h=11, l=9.5, c=10.8)))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertEqual(inv.entry.entry_date, "20240103")

        # T+0: settlement gate blocks stop on entry day
        self.assertTrue(inv.tick(_tick("20240103", o=10.5, h=11, l=8.0, c=9.0)))

        self.assertFalse(inv.tick(_tick("20240104", o=9.5, h=10, l=7.5, c=8.0)))
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertEqual(inv.exit_info.exit_reason, "stop_loss")


class TestInvestmentTakeProfit(unittest.TestCase):
    def test_take_profit_trigger(self) -> None:
        settings = _settings(goal={"take_profit": {"stages": [{"ratio": 0.1, "close_invest": True}]}})
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        inv.tick(_tick("20240103", o=10, h=11, l=9.5, c=10))
        self.assertFalse(inv.tick(_tick("20240104", o=10, h=12.0, l=9.8, c=11.5)))
        self.assertEqual(inv.exit_info.exit_reason, "take_profit")


class TestInvestmentExpiration(unittest.TestCase):
    def test_expiration_open_day(self) -> None:
        settings = _settings(
            goal={"expiration": {"fixed_window_in_days": 2, "mode": "open_day"}},
        )
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        inv.tick(_tick("20240103", o=10, h=10.5, l=9.8, c=10.2))
        self.assertFalse(inv.tick(_tick("20240104", o=10.2, h=10.5, l=10.0, c=10.3)))
        self.assertEqual(inv.exit_info.exit_reason, "expired")


class TestInvestmentToOpportunity(unittest.TestCase):
    def test_to_opportunity_strips_runtime_results(self) -> None:
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH", name="浦发银行"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
            trigger_price_raw=20.0,
        )
        inv = _inv(opp, settings)
        inv.meta.opportunity_id = "opp-1"
        inv.tick(_tick("20240103", o=10.5, h=11, l=9.5, c=10.8))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)

        projected = inv.to_opportunity()
        self.assertIsInstance(projected, Opportunity)
        self.assertNotIsInstance(projected, Investment)
        self.assertEqual(projected.meta.opportunity_id, "opp-1")
        self.assertEqual(projected.trigger_price_raw, 20.0)
        self.assertFalse(hasattr(projected, "runtime_state") and projected.__dict__.get("runtime_state"))
        dumped = projected.to_dict()
        self.assertNotIn("runtime_state", dumped)
        self.assertNotIn("deps", dumped)
        self.assertNotIn("entry", dumped)


class TestInvestmentRawPrices(unittest.TestCase):
    def test_entry_and_exit_record_raw_from_bar(self) -> None:
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar(
                "20240102",
                o=10,
                h=11,
                l=9,
                c=10,
                raw={"open": 20, "high": 22, "low": 18, "close": 20},
            ),
            trigger_date="20240102",
            trigger_price=10.0,
            trigger_price_raw=20.0,
        )
        inv = _inv(opp, settings)
        inv.meta.opportunity_id = "1"
        self.assertEqual(inv.trigger_price_raw, 20.0)

        self.assertTrue(
            inv.tick(
                _tick(
                    "20240103",
                    o=10.5,
                    h=11,
                    l=9.5,
                    c=10.8,
                    raw={"open": 21.0, "high": 22, "low": 19, "close": 21.5},
                )
            )
        )
        self.assertEqual(inv.entry.entry_price, 10.5)
        self.assertEqual(inv.entry.entry_price_raw, 21.0)

        self.assertFalse(
            inv.tick(
                _tick(
                    "20240104",
                    o=9.5,
                    h=10,
                    l=7.5,
                    c=8.0,
                    raw={"open": 19, "high": 20, "low": 15, "close": 16.0},
                )
            )
        )
        self.assertEqual(inv.exit_info.exit_price, 8.0)
        self.assertEqual(inv.exit_info.exit_price_raw, 16.0)
        self.assertEqual(inv.completed_goals[0]["price_raw"], 16.0)

        from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
            InvestmentRow,
        )

        row = InvestmentRow.from_payload(inv.to_dict())
        self.assertEqual(row.trigger_price_raw, 20.0)
        self.assertEqual(row.entry_price_raw, 21.0)
        self.assertEqual(row.exit_price_raw, 16.0)


class TestGoalSettingsExpiration(unittest.TestCase):
    def test_parse_expiration_mode(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {"expiration": {"fixed_window_in_days": 10, "mode": "trading_day"}},
            }
        )
        exp = settings.goal.expiration
        self.assertIsNotNone(exp)
        assert exp is not None
        self.assertEqual(exp.mode, "trading_day")


if __name__ == "__main__":
    unittest.main()
