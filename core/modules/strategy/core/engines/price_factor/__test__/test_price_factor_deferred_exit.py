"""Price Factor：跌停卖出顺延（deferred exit）与持仓锁。"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from core.modules.market_profile import MarketRulesProxy
from core.modules.strategy.core.services.artifacts import (
    InvestmentRow,
)
from core.modules.strategy.core.engines.price_factor.executor import PriceFactorJobExecutor
from core.modules.strategy.core.engines.price_factor.helpers.deferred_exit import (
    retry_deferred_exits,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def _row(**kwargs) -> InvestmentRow:
    base = dict(
        investment_id="1",
        trigger_date="20240101",
        trigger_price=10.0,
        entry_date="20240102",
        entry_price=10.0,
        entry_price_hfq=10.0,
        exit_date="20240110",
        exit_price=9.0,
        exit_price_hfq=9.0,
        exit_reason="stop_loss",
        lifecycle="complete",
        result="loss",
        weighted_roi=-0.1,
        holding_days=8,
        exit_at_limit=None,
        enter_at_limit=None,
    )
    base.update(kwargs)
    if "entry_price_hfq" not in kwargs:
        base["entry_price_hfq"] = float(base.get("entry_price") or 0.0)
    if "exit_price_hfq" not in kwargs:
        base["exit_price_hfq"] = float(base.get("exit_price") or 0.0)
    return InvestmentRow(**base)


def _bar(
    date: str,
    *,
    o: float,
    h: float,
    l: float,
    c: float,
    pre: float | None = None,
    hfq: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "date": date,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
    }
    if pre is not None:
        row["pre_close"] = pre
    if hfq is None:
        hfq = {"open": o, "high": h, "low": l, "close": c}
        if pre is not None:
            hfq["pre_close"] = pre
    row["hfq"] = hfq
    return row


def _settings(**edge_overrides) -> StrategySettings:
    edges = {
        "allow_enter_at_limit_up": False,
        "allow_exit_at_limit_down": False,
    }
    edges.update(edge_overrides)
    settings = StrategySettings.from_dict(
        {
            "simulation": {
                "assumption": {
                    "template": "none",
                    "tradability": {"edges": edges},
                },
                "risk_control": {},
            }
        }
    )
    settings.apply_defaults()
    return settings


def test_retry_deferred_fills_on_next_non_limit_bar() -> None:
    rules = MarketRulesProxy.for_market("china_a_stock")
    skipped = [
        {
            "date": "20240110",
            "exit_price": 9.0,
            "exit_ratio": 1.0,
            "reason": "stop_loss",
            "exit_at_limit": True,
        }
    ]
    klines = [
        _bar("20240110", o=9.0, h=9.0, l=9.0, c=9.0, pre=10.0),
        _bar("20240111", o=9.5, h=9.7, l=9.4, c=9.6, pre=9.0),
    ]
    processed, pending, skips = retry_deferred_exits(
        enter_price=10.0,
        enter_price_hfq=10.0,
        processed_legs=[],
        skipped_legs=skipped,
        klines=klines,
        entity_id="600000.SH",
        settings=_settings(allow_exit_at_limit_down=False),
        market_rules=rules,
    )
    assert pending is None
    assert len(processed) == 1
    assert processed[0]["date"] == "20240111"
    assert processed[0]["exit_price"] == pytest.approx(9.6)
    assert processed[0]["exit_price_hfq"] == pytest.approx(9.6)
    assert processed[0]["roi"] == pytest.approx(-0.04)
    assert skips == 0


def test_replay_deferred_exit_moves_sell_date() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240110",
            exit_price=9.0,
            exit_at_limit=True,
        ),
        _row(
            investment_id="2",
            entry_date="20240111",
            exit_date="20240115",
            exit_price=11.0,
            exit_at_limit=False,
            weighted_roi=0.1,
            result="win",
        ),
    ]
    klines = [
        _bar("20240110", o=9.0, h=9.0, l=9.0, c=9.0),
        _bar("20240111", o=9.5, h=9.6, l=9.4, c=9.5),
        _bar("20240115", o=11.0, h=11.1, l=10.9, c=11.0),
    ]

    def _loader(_sid: str, *, start_date: str, end_date: str, **_kw) -> List[Dict[str, Any]]:
        _ = (start_date, end_date)
        return klines

    out, skipped = PriceFactorJobExecutor._replay_entity_investments(
        rows,
        entity_id="600000.SH",
        backtest_end="20240131",
        settings=_settings(allow_exit_at_limit_down=False),
        load_klines=_loader,
    )
    assert skipped >= 1
    assert [r.opportunity_id for r in out] == ["1"]
    assert out[0].exit_date == "20240111"
    assert out[0].lifecycle == "complete"
    assert out[0].exit_price == pytest.approx(9.5)
    assert out[0].exit_price_hfq == pytest.approx(9.5)
    assert out[0].roi == pytest.approx(-0.05)


def test_replay_stuck_at_limit_locks_until_end() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240110",
            exit_price=9.0,
            exit_at_limit=True,
        ),
        _row(
            investment_id="2",
            entry_date="20240120",
            exit_date="20240122",
            exit_price=11.0,
            exit_at_limit=False,
        ),
    ]
    # 全程贴板：pre_close 与 close 构成跌停
    klines = [
        _bar("20240110", o=9.0, h=9.0, l=9.0, c=9.0, pre=10.0),
        _bar("20240111", o=8.1, h=8.1, l=8.1, c=8.1, pre=9.0),
        _bar("20240120", o=7.29, h=7.29, l=7.29, c=7.29, pre=8.1),
    ]
    rules = MarketRulesProxy.for_market("china_a_stock")

    def _loader(_sid: str, *, start_date: str, end_date: str, **_kw) -> List[Dict[str, Any]]:
        _ = (start_date, end_date)
        return klines

    out, skipped = PriceFactorJobExecutor._replay_entity_investments(
        rows,
        entity_id="600000.SH",
        backtest_end="20240131",
        settings=_settings(allow_exit_at_limit_down=False),
        market_rules=rules,
        load_klines=_loader,
    )
    assert skipped >= 1
    assert [r.opportunity_id for r in out] == ["1"]
    assert out[0].lifecycle == "open"
    assert out[0].exit_date == ""


def test_replay_allow_exit_at_limit_down_trusts_enum() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240110",
            exit_price=9.0,
            exit_at_limit=True,
            weighted_roi=-0.1,
        ),
    ]
    called = {"n": 0}

    def _loader(_sid: str, *, start_date: str, end_date: str, **_kw) -> List[Dict[str, Any]]:
        called["n"] += 1
        return []

    out, skipped = PriceFactorJobExecutor._replay_entity_investments(
        rows,
        entity_id="600000.SH",
        backtest_end="20240131",
        settings=_settings(allow_exit_at_limit_down=True),
        load_klines=_loader,
    )
    assert called["n"] == 0
    assert skipped == 0
    assert len(out) == 1
    assert out[0].exit_date == "20240110"
    assert out[0].exit_price == pytest.approx(9.0)


def test_replay_skips_buy_at_limit_up() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="20240105",
            enter_at_limit=True,
        ),
        _row(
            investment_id="2",
            entry_date="20240106",
            exit_date="20240108",
            enter_at_limit=False,
        ),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(
        rows,
        settings=_settings(allow_enter_at_limit_up=False),
    )
    assert [r.opportunity_id for r in out] == ["2"]


def test_deferred_exit_roi_uses_hfq_not_qfq_split() -> None:
    """跌停顺延后的成交日若 10 送 10：qfq 腰斩，hfq 持平附近 → ROI 不能是 −50%。"""
    rules = MarketRulesProxy.for_market("china_a_stock")
    skipped = [
        {
            "date": "20240110",
            "exit_price": 9.0,
            "exit_price_hfq": 18.0,
            "exit_ratio": 1.0,
            "reason": "stop_loss",
            "exit_at_limit": True,
        }
    ]
    klines = [
        _bar("20240110", o=9.0, h=9.0, l=9.0, c=9.0, pre=10.0),
        _bar(
            "20240111",
            o=5.0,
            h=5.1,
            l=4.95,
            c=5.05,
            pre=5.0,
            hfq={
                "open": 10.0,
                "high": 10.2,
                "low": 9.9,
                "close": 10.1,
                "pre_close": 10.0,
            },
        ),
    ]
    processed, pending, skips = retry_deferred_exits(
        enter_price=10.0,
        enter_price_hfq=10.0,
        processed_legs=[],
        skipped_legs=skipped,
        klines=klines,
        entity_id="600000.SH",
        settings=_settings(allow_exit_at_limit_down=False),
        market_rules=rules,
    )
    assert pending is None
    assert skips == 0
    assert len(processed) == 1
    assert processed[0]["date"] == "20240111"
    assert processed[0]["exit_price"] == pytest.approx(5.05)
    assert processed[0]["exit_price_hfq"] == pytest.approx(10.1)
    assert processed[0]["roi"] == pytest.approx(0.01)

    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            entry_price=10.0,
            entry_price_hfq=10.0,
            exit_date="20240110",
            exit_price=9.0,
            exit_price_hfq=18.0,
            exit_at_limit=True,
            weighted_roi=-0.1,
            result="loss",
        )
    ]

    def _loader(_sid: str, *, start_date: str, end_date: str, **_kw) -> List[Dict[str, Any]]:
        _ = (start_date, end_date)
        return klines

    out, skipped_n = PriceFactorJobExecutor._replay_entity_investments(
        rows,
        entity_id="600000.SH",
        backtest_end="20240131",
        settings=_settings(allow_exit_at_limit_down=False),
        market_rules=rules,
        load_klines=_loader,
    )
    assert skipped_n >= 1
    assert len(out) == 1
    assert out[0].exit_date == "20240111"
    assert out[0].lifecycle == "complete"
    assert out[0].exit_price == pytest.approx(5.05)
    assert out[0].exit_price_hfq == pytest.approx(10.1)
    assert out[0].roi == pytest.approx(0.01)
    assert out[0].result == "win"


def test_deferred_exit_missing_hfq_leg_roi_is_zero() -> None:
    rules = MarketRulesProxy.for_market("china_a_stock")
    skipped = [
        {
            "date": "20240110",
            "exit_price": 9.0,
            "exit_ratio": 1.0,
            "reason": "stop_loss",
            "exit_at_limit": True,
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
    processed, pending, _skips = retry_deferred_exits(
        enter_price=10.0,
        enter_price_hfq=10.0,
        processed_legs=[],
        skipped_legs=skipped,
        klines=klines,
        entity_id="600000.SH",
        settings=_settings(allow_exit_at_limit_down=False),
        market_rules=rules,
    )
    assert pending is None
    assert len(processed) == 1
    assert processed[0]["exit_price"] == pytest.approx(9.6)
    assert processed[0]["exit_price_hfq"] == pytest.approx(0.0)
    assert processed[0]["roi"] == pytest.approx(0.0)
