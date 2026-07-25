"""PENDING_TO_ENTER：touch 成交 + pending_enter 挂单风控。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.shared.data_class import Investment, Lifecycle
from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    StockInfo,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

OPEN_DATES = ("20240102", "20240103", "20240104", "20240105", "20240108", "20240109")


def _bar(date: str, *, o: float, h: float, l: float, c: float) -> dict:
    return {"date": date, "open": o, "high": h, "low": l, "close": c, "pre_close": o}


def _settings(**kwargs) -> StrategySettings:
    enter_price = kwargs.pop("enter_price", "next_open")
    pending = kwargs.pop("pending_enter", {})
    raw = {
        "simulation": {
            "execution": {"mode": "entity_based"},
            "assumption": {
                "template": "none",
                "tradability": {
                    "enter_price": enter_price,
                    "exit_price": "close",
                    "edges": {"allow_enter_at_limit_up": True},
                },
            },
            "risk_control": {
                "skip_enter_when": [],
                "force_exit_when": [],
                "pending_enter": {
                    "max_wait_open_days": 5,
                    "max_entry_drift": None,
                    "abort_enter_when": [],
                    **pending,
                },
            },
        }
    }
    return StrategySettings.from_dict(raw)


def _inv(
    *,
    trigger_date: str = "20240102",
    trigger_price: float = 10.0,
    enter_price: str = "touch",
    pending_enter: dict | None = None,
    delist_date: str = "",
) -> Investment:
    settings = _settings(
        enter_price=enter_price,
        pending_enter=pending_enter or {},
    )
    settings.apply_defaults()
    opp = Opportunity(
        stock=StockInfo(id="000001", delist_date=delist_date),
        record_of_today=_bar(trigger_date, o=10, h=11, l=9, c=trigger_price),
    )
    opp.bind_scan_context(
        strategy_name="t",
        stock_id="000001",
        stock_info={"id": "000001", "delist_date": delist_date},
        trigger_date=trigger_date,
        trigger_price=trigger_price,
    )
    return Investment.create_from_opportunity(
        opp,
        settings=settings,
        open_dates=OPEN_DATES,
    )


def test_pending_enter_defaults_in_risk_control() -> None:
    settings = _settings()
    settings.apply_defaults()
    pe = settings.simulation.risk_control.pending_enter
    assert pe.max_wait_open_days == 5
    assert pe.max_entry_drift is None
    dumped = settings.simulation.to_dict()["risk_control"]["pending_enter"]
    assert dumped["max_wait_open_days"] == 5
    assert dumped["max_entry_drift"] is None


def test_touch_fills_when_range_hits_limit() -> None:
    inv = _inv(trigger_price=10.0, enter_price="touch")
    assert inv.lifecycle == Lifecycle.PENDING_TO_ENTER
    inv.try_enter("20240103", _bar("20240103", o=11, h=11.5, l=10.0, c=10.5))
    assert inv.lifecycle == Lifecycle.OPEN
    assert inv.entry.price == pytest.approx(10.0)


def test_touch_waits_when_not_touched() -> None:
    inv = _inv(trigger_price=10.0, enter_price="touch")
    inv.try_enter("20240103", _bar("20240103", o=11, h=11.5, l=10.5, c=11.0))
    assert inv.lifecycle == Lifecycle.PENDING_TO_ENTER


def test_max_wait_open_days_aborts_after_n_trade_days() -> None:
    inv = _inv(
        enter_price="touch",
        trigger_price=10.0,
        pending_enter={"max_wait_open_days": 2},
    )
    # day1: miss
    inv.try_enter("20240103", _bar("20240103", o=11, h=12, l=11, c=11.5))
    assert inv.lifecycle == Lifecycle.PENDING_TO_ENTER
    # day2: miss → exhausted → abort
    inv.try_enter("20240104", _bar("20240104", o=11, h=12, l=11, c=11.5))
    assert inv.lifecycle == Lifecycle.COMPLETE
    assert "max_wait_open_days" in inv.exit_info.reason
    assert inv.entry.price == 0.0


def test_max_entry_drift_aborts_on_gap_open() -> None:
    inv = _inv(
        enter_price="next_open",
        trigger_price=10.0,
        pending_enter={"max_entry_drift": 0.05},
    )
    # open 12 → 20% drift → abort
    inv.try_enter("20240103", _bar("20240103", o=12, h=12.5, l=11.5, c=12.0))
    assert inv.lifecycle == Lifecycle.COMPLETE
    assert "max_entry_drift" in inv.exit_info.reason


def test_delisted_aborts_pending_enter() -> None:
    inv = _inv(
        enter_price="next_open",
        delist_date="20240103",
    )
    inv.try_enter("20240103", _bar("20240103", o=10, h=10.5, l=9.5, c=10.0))
    assert inv.lifecycle == Lifecycle.COMPLETE
    assert "delisted" in inv.exit_info.reason
