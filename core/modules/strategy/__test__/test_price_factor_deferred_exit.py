"""Price Factor：跌停卖出顺延（deferred exit）与持仓锁。"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from core.modules.market_profile.core.markets import create_market_rules
from core.modules.strategy.core.engines.shared.services.simulation_input.stock_investments import (
    InvestmentRow,
)
from core.modules.strategy.core.engines.price_factor.executor import JobExecutor
from core.modules.strategy.core.engines.price_factor.helpers.deferred_exit import (
    retry_deferred_exits,
)

pytestmark = pytest.mark.force_run


def _row(**kwargs) -> InvestmentRow:
    base = dict(
        investment_id="1",
        trigger_date="20240101",
        trigger_price=10.0,
        entry_date="20240102",
        entry_price=10.0,
        exit_date="20240110",
        exit_price=9.0,
        exit_reason="stop_loss",
        lifecycle="complete",
        result="loss",
        weighted_roi=-0.1,
        holding_days=8,
        sell_at_limit_down=None,
        buy_at_limit_up=None,
    )
    base.update(kwargs)
    return InvestmentRow(**base)


def test_retry_deferred_fills_on_next_non_limit_bar() -> None:
    rules = create_market_rules("china_a_stock")
    skipped = [
        {
            "date": "20240110",
            "sell_price": 9.0,
            "exit_ratio": 1.0,
            "reason": "stop_loss",
            "sell_at_limit_down": True,
        }
    ]
    klines = [
        {
            "date": "20240110",
            "open": 9.0,
            "close": 9.0,
            "high": 9.0,
            "low": 9.0,
            "pre_close": 10.0,
        },
        {
            "date": "20240111",
            "open": 9.5,
            "close": 9.6,
            "high": 9.7,
            "low": 9.4,
            "pre_close": 9.0,
        },
    ]
    processed, pending, skips = retry_deferred_exits(
        buy_price=10.0,
        processed_legs=[],
        skipped_legs=skipped,
        klines=klines,
        entity_id="600000.SH",
        market_rules=rules,
        allow_exit_at_limit_down=False,
    )
    assert pending is None
    assert len(processed) == 1
    assert processed[0]["date"] == "20240111"
    assert processed[0]["sell_price"] == pytest.approx(9.6)
    assert skips == 0


def test_replay_deferred_exit_moves_sell_date() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240110",
            exit_price=9.0,
            sell_at_limit_down=True,
        ),
        _row(
            investment_id="2",
            entry_date="20240111",
            exit_date="20240115",
            exit_price=11.0,
            sell_at_limit_down=False,
            weighted_roi=0.1,
            result="win",
        ),
    ]
    klines = [
        {"date": "20240110", "open": 9.0, "close": 9.0, "high": 9.0, "low": 9.0},
        {"date": "20240111", "open": 9.5, "close": 9.5, "high": 9.6, "low": 9.4},
        {"date": "20240115", "open": 11.0, "close": 11.0, "high": 11.1, "low": 10.9},
    ]

    def _loader(_sid: str, *, start_date: str, end_date: str, **_kw) -> List[Dict[str, Any]]:
        _ = (start_date, end_date)
        return klines

    out, skipped = JobExecutor._replay_entity_investments(
        rows,
        entity_id="600000.SH",
        backtest_end="20240131",
        allow_exit_at_limit_down=False,
        load_klines=_loader,
    )
    assert skipped >= 1
    assert [r.opportunity_id for r in out] == ["1"]
    assert out[0].sell_date == "20240111"
    assert out[0].lifecycle == "complete"
    assert out[0].sell_price == pytest.approx(9.5)


def test_replay_stuck_at_limit_locks_until_end() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240110",
            exit_price=9.0,
            sell_at_limit_down=True,
        ),
        _row(
            investment_id="2",
            entry_date="20240120",
            exit_date="20240122",
            exit_price=11.0,
            sell_at_limit_down=False,
        ),
    ]
    # 全程贴板：pre_close 与 close 构成跌停
    klines = [
        {
            "date": "20240110",
            "open": 9.0,
            "close": 9.0,
            "high": 9.0,
            "low": 9.0,
            "pre_close": 10.0,
        },
        {
            "date": "20240111",
            "open": 8.1,
            "close": 8.1,
            "high": 8.1,
            "low": 8.1,
            "pre_close": 9.0,
        },
        {
            "date": "20240120",
            "open": 7.29,
            "close": 7.29,
            "high": 7.29,
            "low": 7.29,
            "pre_close": 8.1,
        },
    ]
    rules = create_market_rules("china_a_stock")

    def _loader(_sid: str, *, start_date: str, end_date: str, **_kw) -> List[Dict[str, Any]]:
        _ = (start_date, end_date)
        return klines

    out, skipped = JobExecutor._replay_entity_investments(
        rows,
        entity_id="600000.SH",
        backtest_end="20240131",
        allow_exit_at_limit_down=False,
        market_rules=rules,
        load_klines=_loader,
    )
    assert skipped >= 1
    assert [r.opportunity_id for r in out] == ["1"]
    assert out[0].lifecycle == "open"
    assert out[0].sell_date == ""


def test_replay_allow_exit_at_limit_down_trusts_enum() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240110",
            exit_price=9.0,
            sell_at_limit_down=True,
            weighted_roi=-0.1,
        ),
    ]
    called = {"n": 0}

    def _loader(_sid: str, *, start_date: str, end_date: str, **_kw) -> List[Dict[str, Any]]:
        called["n"] += 1
        return []

    out, skipped = JobExecutor._replay_entity_investments(
        rows,
        entity_id="600000.SH",
        backtest_end="20240131",
        allow_exit_at_limit_down=True,
        load_klines=_loader,
    )
    assert called["n"] == 0
    assert skipped == 0
    assert len(out) == 1
    assert out[0].sell_date == "20240110"
    assert out[0].sell_price == pytest.approx(9.0)


def test_replay_skips_buy_at_limit_up() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240105",
            buy_at_limit_up=True,
        ),
        _row(
            investment_id="2",
            entry_date="20240106",
            exit_date="20240108",
            buy_at_limit_up=False,
        ),
    ]
    out, _ = JobExecutor._replay_entity_investments(
        rows,
        allow_enter_at_limit_up=False,
    )
    assert [r.opportunity_id for r in out] == ["2"]
