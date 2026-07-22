#!/usr/bin/env python3
"""Investment.tick 单元测试。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run

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
    pre_close: float | None = None,
    raw: dict | None = None,
) -> dict:
    row = {"date": date, "open": o, "high": h, "low": l, "close": c}
    if pre_close is not None:
        row["pre_close"] = pre_close
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
    pre_close: float | None = None,
    raw: dict | None = None,
) -> InvestmentTickInput:
    return InvestmentTickInput(
        as_of_date=date,
        bar=_bar(date, o=o, h=h, l=l, c=c, pre_close=pre_close, raw=raw),
        data_as_of=date,
    )


def _settings(**overrides) -> StrategySettings:
    raw: dict = {
        "simulation": {
            "buy_price_model": "next_open",
            "sell_price_model": "close",
            "execute_steps": [
                "check_settlement",
                "check_stop_loss",
                "check_take_profit",
                "check_expiration",
            ],
            "edges": {
                "allow_buy_at_limit_up": False,
                "allow_sell_at_limit_down": False,
            },
        },
        "goal": {
            "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
            "take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]},
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        },
    }
    for key, value in overrides.items():
        if key in ("simulation", "goal") and isinstance(value, dict):
            block = raw.setdefault(key, {})
            for nested_key, nested_value in value.items():
                if nested_key == "edges" and isinstance(nested_value, dict):
                    edges = block.setdefault("edges", {})
                    edges.update(nested_value)
                else:
                    block[nested_key] = nested_value
        else:
            raw[key] = value
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


class TestInvestmentLimitTradability(unittest.TestCase):
    def test_buy_blocked_at_limit_up_then_retries_next_day(self) -> None:
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)

        # 次日开盘涨停（pre_close=10 → limit_up=11）→ 不买
        self.assertTrue(
            inv.tick(_tick("20240103", o=11.0, h=11.0, l=10.5, c=11.0, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.PENDING_TO_ENTER)

        # 再下一日开盘未涨停 → 买入
        self.assertTrue(
            inv.tick(_tick("20240104", o=10.5, h=11.0, l=10.0, c=10.8, pre_close=11.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertEqual(inv.entry.entry_date, "20240104")
        self.assertEqual(inv.entry.entry_price, 10.5)

    def test_allow_buy_at_limit_up_fills(self) -> None:
        settings = _settings(
            simulation={
                "edges": {
                    "allow_buy_at_limit_up": True,
                    "allow_sell_at_limit_down": False,
                }
            }
        )
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        self.assertTrue(
            inv.tick(_tick("20240103", o=11.0, h=11.0, l=10.8, c=11.0, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertEqual(inv.entry.entry_price, 11.0)

    def test_sell_blocked_at_limit_down_then_retries(self) -> None:
        settings = _settings(
            goal={"stop_loss": {"stages": [{"ratio": -0.05, "close_invest": True}]}}
        )
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        inv.tick(_tick("20240103", o=10.0, h=10.5, l=9.8, c=10.0, pre_close=10.0))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)

        # T+1：触发止损，但收盘贴跌停（pre=10 → down=9）→ 挂起
        self.assertTrue(
            inv.tick(_tick("20240104", o=9.8, h=9.9, l=9.0, c=9.0, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.PENDING_TO_EXIT)
        self.assertFalse(bool(inv.exit_info.exit_date))

        # 次日收盘离开跌停 → 卖出
        self.assertFalse(
            inv.tick(_tick("20240105", o=9.2, h=9.5, l=9.1, c=9.3, pre_close=9.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertEqual(inv.exit_info.exit_reason, "stop_loss")
        self.assertEqual(inv.exit_info.exit_price, 9.3)

    def test_missing_pre_close_does_not_block(self) -> None:
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        # 开盘 11 若无 pre_close 则无法判涨停 → 允许成交
        self.assertTrue(inv.tick(_tick("20240103", o=11.0, h=11.0, l=10.5, c=11.0)))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertIsNone(inv.entry.buy_at_limit_up)
        self.assertIsNone(inv.entry.buy_prev_close)

    def test_fill_stamps_limit_flags_on_entry_and_exit(self) -> None:
        settings = _settings(
            simulation={
                "edges": {
                    "allow_buy_at_limit_up": True,
                    "allow_sell_at_limit_down": True,
                }
            },
            goal={"stop_loss": {"stages": [{"ratio": -0.05, "close_invest": True}]}},
        )
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        inv.meta.opportunity_id = "opp-limit-stamp"
        inv.tick(_tick("20240103", o=11.0, h=11.0, l=10.8, c=11.0, pre_close=10.0))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertTrue(inv.entry.buy_at_limit_up)
        self.assertEqual(inv.entry.buy_prev_close, 10.0)

        self.assertFalse(
            inv.tick(_tick("20240104", o=9.8, h=9.9, l=9.0, c=9.0, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertTrue(inv.exit_info.sell_at_limit_down)
        self.assertEqual(inv.exit_info.sell_prev_close, 10.0)

        from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
            InvestmentRow,
        )

        row = InvestmentRow.from_payload(inv.to_dict())
        self.assertTrue(row.buy_at_limit_up)
        self.assertTrue(row.sell_at_limit_down)
        csv_row = row.to_csv_row()
        self.assertEqual(csv_row["buy_at_limit_up"], "1")
        self.assertEqual(csv_row["sell_at_limit_down"], "1")
        roundtrip = InvestmentRow.from_csv_row(csv_row)
        self.assertTrue(roundtrip.buy_at_limit_up)
        self.assertTrue(roundtrip.sell_at_limit_down)


if __name__ == "__main__":
    unittest.main()
