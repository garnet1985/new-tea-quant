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
                    "edges": {
                        "allow_enter_at_limit_up": False,
                        "allow_exit_at_limit_down": False,
                    },
                },
            },
            "risk_control": {},
        },
        "goal": {
            "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
            "take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]},
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        },
    }
    for key, value in overrides.items():
        if key == "simulation" and isinstance(value, dict):
            sim = raw.setdefault("simulation", {})
            for nested_key, nested_value in value.items():
                if nested_key == "edges" and isinstance(nested_value, dict):
                    tradability = (
                        sim.setdefault("assumption", {})
                        .setdefault("tradability", {})
                    )
                    edges = tradability.setdefault("edges", {})
                    edges.update(nested_value)
                elif nested_key in {"enter_price", "exit_price", "monitor_price"}:
                    tradability = (
                        sim.setdefault("assumption", {})
                        .setdefault("tradability", {})
                    )
                    tradability[nested_key] = nested_value
                else:
                    sim[nested_key] = nested_value
        elif key == "goal" and isinstance(value, dict):
            block = raw.setdefault("goal", {})
            block.update(value)
        else:
            raw[key] = value
    settings = StrategySettings(raw_settings=raw)
    settings.apply_defaults()
    return settings


def _inv(
    opp: Opportunity,
    settings: StrategySettings,
    *,
    status_tags_provider=None,
) -> Investment:
    opp.market_profile = "china_a_stock"
    return Investment.create_from_opportunity(
        opp,
        settings=settings,
        open_dates=OPEN_DATES,
        status_tags_provider=status_tags_provider,
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

    def test_allow_enter_at_limit_up_fills(self) -> None:
        settings = _settings(
            simulation={
                "edges": {
                    "allow_enter_at_limit_up": True,
                    "allow_exit_at_limit_down": False,
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
                    "allow_enter_at_limit_up": True,
                    "allow_exit_at_limit_down": True,
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


class _FixedStatusTags:
    """测试用 status_tags_provider：固定返回给定 tags。"""

    def __init__(self, tags_by_date: dict[str, list[str]]) -> None:
        self._tags_by_date = tags_by_date

    def status_tags_at(self, entity_id: str, trade_date: str) -> list[str]:
        return list(self._tags_by_date.get(str(trade_date), []))


class TestInvestmentStStatusTagsLimit(unittest.TestCase):
    def test_st_day_uses_five_percent_band_for_buy_block(self) -> None:
        """ST 日：pre_close=10 → 涨停 10.5；10.5 应被挡，10.4 可买。"""
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        provider = _FixedStatusTags({"20240103": ["st"], "20240104": ["st"]})
        inv = _inv(opp, settings, status_tags_provider=provider)

        # 无 ST 时 10.5 不是 10% 涨停；有 ST 时是 5% 涨停 → 不买
        self.assertTrue(
            inv.tick(_tick("20240103", o=10.5, h=10.5, l=10.2, c=10.5, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.PENDING_TO_ENTER)

        self.assertTrue(
            inv.tick(_tick("20240104", o=10.4, h=10.6, l=10.2, c=10.5, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertEqual(inv.entry.entry_price, 10.4)

    def test_without_provider_ten_percent_band(self) -> None:
        """无 provider 时仍按主板 10%：开盘 10.5 可买。"""
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        self.assertTrue(
            inv.tick(_tick("20240103", o=10.5, h=10.8, l=10.2, c=10.6, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertEqual(inv.entry.entry_price, 10.5)

    def test_st_day_sell_block_at_five_percent_down(self) -> None:
        settings = _settings(
            goal={"stop_loss": {"stages": [{"ratio": -0.02, "close_invest": True}]}}
        )
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        provider = _FixedStatusTags(
            {
                "20240103": [],
                "20240104": ["st"],
                "20240105": ["st"],
            }
        )
        inv = _inv(opp, settings, status_tags_provider=provider)
        inv.tick(_tick("20240103", o=10.0, h=10.2, l=9.9, c=10.0, pre_close=10.0))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)

        # ST 跌停 = 9.5；收盘贴板 → 挂起
        self.assertTrue(
            inv.tick(_tick("20240104", o=9.8, h=9.9, l=9.5, c=9.5, pre_close=10.0))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.PENDING_TO_EXIT)

        self.assertFalse(
            inv.tick(_tick("20240105", o=9.6, h=9.7, l=9.55, c=9.6, pre_close=9.5))
        )
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertEqual(inv.exit_info.exit_price, 9.6)

    def test_enum_output_stamps_stock_status_at_trigger(self) -> None:
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        provider = _FixedStatusTags({"20240102": ["st", "star_st"]})
        inv = _inv(opp, settings, status_tags_provider=provider)
        inv.meta.opportunity_id = "opp-st-stamp"

        self.assertEqual(inv.status_tags_at_trigger(), ("st", "star_st"))
        self.assertEqual(
            inv.metadata[Opportunity.STATUS_AT_TRIGGER_KEY], ["st", "star_st"]
        )
        # 源 Opportunity 同步打标
        self.assertEqual(opp.status_tags_at_trigger(), ("st", "star_st"))

        from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
            InvestmentRow,
        )

        # 需 entry/exit 结构：走一轮最小成交
        inv.tick(_tick("20240103", o=10.0, h=10.5, l=9.8, c=10.2, pre_close=10.0))
        row = InvestmentRow.from_payload(inv.to_dict())
        self.assertEqual(row.stock_status_at_trigger, ("st", "star_st"))
        csv_row = row.to_csv_row()
        self.assertEqual(csv_row["stock_status_at_trigger"], '["st", "star_st"]')
        roundtrip = InvestmentRow.from_csv_row(csv_row)
        self.assertEqual(roundtrip.stock_status_at_trigger, ("st", "star_st"))
        projected = roundtrip.to_opportunity("600000.SH")
        self.assertEqual(projected.status_tags_at_trigger(), ("st", "star_st"))

    def test_without_provider_does_not_stamp_status_key(self) -> None:
        settings = _settings()
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        self.assertNotIn(Opportunity.STATUS_AT_TRIGGER_KEY, inv.metadata)
        self.assertEqual(inv.status_tags_at_trigger(), ())


class _TagProvider:
    def __init__(self, mapping):
        self.mapping = mapping

    def status_tags_at(self, entity_id: str, trade_date: str):
        return list(self.mapping.get((entity_id, trade_date), ()))


class TestInvestmentForceExit(unittest.TestCase):
    def test_force_exit_on_st_tag(self) -> None:
        settings = _settings(
            simulation={
                "risk_control": {"force_exit_when": ["st"]},
                "enter_price": "close",
                "exit_price": "close",
            },
            goal={
                "stop_loss": None,
                "take_profit": None,
                "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
            },
        )
        # goal None override may not work via _settings — clear stages after
        settings.raw_settings["goal"] = {
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        }
        settings.apply_defaults()

        provider = _TagProvider({("600000.SH", "20240104"): ("st",)})
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings, status_tags_provider=provider)

        self.assertTrue(inv.tick(_tick("20240102", o=10, h=11, l=9, c=10)))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        # T+1 settlement day
        self.assertTrue(inv.tick(_tick("20240103", o=10, h=11, l=9, c=10.5)))
        self.assertFalse(inv.tick(_tick("20240104", o=10, h=11, l=9, c=9.5)))
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertEqual(inv.exit_info.exit_reason, "stock_status:st")
        self.assertEqual(inv.exit_info.exit_price, 9.5)

    def test_force_exit_partial_ratio_stays_open(self) -> None:
        settings = _settings(
            simulation={
                "risk_control": {
                    "force_exit_when": [
                        {"status": "st", "close_invest": False, "exit_ratio": 0.5},
                    ]
                },
                "enter_price": "close",
                "exit_price": "close",
            },
        )
        settings.raw_settings["goal"] = {
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        }
        settings.apply_defaults()

        provider = _TagProvider({("600000.SH", "20240104"): ("st",)})
        opp = Opportunity(
            stock=StockInfo(id="600000.SH"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings, status_tags_provider=provider)
        inv.tick(_tick("20240102", o=10, h=11, l=9, c=10))
        inv.tick(_tick("20240103", o=10, h=11, l=9, c=10.5))
        self.assertTrue(inv.tick(_tick("20240104", o=10, h=11, l=9, c=9.0)))
        self.assertEqual(inv.lifecycle, Lifecycle.OPEN)
        self.assertEqual(len(inv.completed_goals), 1)
        self.assertEqual(inv.completed_goals[0]["exit_ratio"], 0.5)
        self.assertEqual(inv.completed_goals[0]["reason"], "stock_status:st")
        self.assertIn("st", inv.runtime_state.triggered_force_exit_tags)
        # 同一 tag 不再二次触发
        self.assertTrue(inv.tick(_tick("20240105", o=10, h=11, l=9, c=9.0)))
        self.assertEqual(len(inv.completed_goals), 1)

    def test_delisted_exit_uses_last_tradable_close(self) -> None:
        settings = _settings(
            simulation={
                "enter_price": "close",
                "exit_price": "close",
                "assumption": {
                    "template": "none",
                    "tradability": {
                        "enter_price": "close",
                        "exit_price": "close",
                        "delisted_exit_price": "last_tradable_close",
                    },
                },
            },
        )
        settings.raw_settings["goal"] = {
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        }
        settings.apply_defaults()

        opp = Opportunity(
            stock=StockInfo(id="600000.SH", delist_date="20240105"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        inv.tick(_tick("20240102", o=10, h=11, l=9, c=10))
        inv.tick(_tick("20240103", o=10, h=11, l=9, c=10.5))
        inv.tick(_tick("20240104", o=10, h=11, l=9, c=12.0))
        self.assertFalse(inv.tick(_tick("20240105", o=10, h=11, l=9, c=1.0)))
        self.assertEqual(inv.lifecycle, Lifecycle.COMPLETE)
        self.assertEqual(inv.exit_info.exit_reason, "stock_status:delisted")
        # 定价用上一根 close=12，不是退市日 close=1
        self.assertEqual(inv.exit_info.exit_price, 12.0)
        self.assertEqual(inv.exit_info.exit_date, "20240104")

    def test_delisted_exit_same_tick_close(self) -> None:
        settings = _settings(
            simulation={
                "assumption": {
                    "template": "none",
                    "tradability": {
                        "enter_price": "close",
                        "exit_price": "close",
                        "delisted_exit_price": "same_tick_close",
                    },
                },
            },
        )
        settings.raw_settings["goal"] = {
            "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        }
        settings.apply_defaults()

        opp = Opportunity(
            stock=StockInfo(id="600000.SH", delist_date="20240105"),
            record_of_today=_bar("20240102", o=10, h=11, l=9, c=10),
            trigger_date="20240102",
            trigger_price=10.0,
        )
        inv = _inv(opp, settings)
        inv.tick(_tick("20240102", o=10, h=11, l=9, c=10))
        inv.tick(_tick("20240103", o=10, h=11, l=9, c=10.5))
        inv.tick(_tick("20240104", o=10, h=11, l=9, c=12.0))
        self.assertFalse(inv.tick(_tick("20240105", o=10, h=11, l=9, c=3.0)))
        self.assertEqual(inv.exit_info.exit_price, 3.0)
        self.assertEqual(inv.exit_info.exit_date, "20240105")


if __name__ == "__main__":
    unittest.main()
