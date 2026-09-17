"""Tests for decision DTO mapping."""

from __future__ import annotations

import json
from types import SimpleNamespace

from core.bff.APIs.strategy.helpers.decision_dto import (
    holdings_message,
    info_message,
    session_list_message,
    session_snapshot,
)


def test_session_snapshot_uses_ticker_stats_and_draft():
    opp = SimpleNamespace(
        local_id=1,
        entity_id="000001.SZ",
        name="平安银行",
        status_tags=("star_st",),
        entry_price_raw=10.0,
        ticker_stats=SimpleNamespace(
            sample_size=2,
            wins=1,
            win_rate=0.5,
            avg_roi=0.1,
            to_dict=lambda: {
                "sample_size": 2,
                "wins": 1,
                "win_rate": 0.5,
                "avg_roi": 0.1,
            },
        ),
    )
    engine = SimpleNamespace(
        dm_id="1",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="picking",
        is_completed=False,
        current_date="20250407",
        draft={1: 100},
        account=SimpleNamespace(
            cash=999_000.0,
            initial_cash=1_000_000.0,
            open_position_count=lambda: 1,
        ),
        allocation=SimpleNamespace(max_portfolio_size=10),
        timeline=SimpleNamespace(
            start_date="20240102",
            end_date="20250630",
            asof_stats=lambda _date: SimpleNamespace(
                to_dict=lambda: {
                    "sample_size": 4,
                    "wins": 1,
                    "win_rate": 0.25,
                    "avg_roi": -0.05,
                }
            )
        ),
        opportunities=lambda: [opp],
        opportunity_by_local=lambda lid: opp if lid == 1 else None,
    )
    msg = session_snapshot(engine)
    assert msg["dm_id"] == "1"
    assert msg["start_date"] == "20240102"
    assert msg["end_date"] == "20250630"
    assert msg["open_position_count"] == 1
    assert msg["opportunities"][0]["stats"]["win_rate"] == 0.5
    assert msg["asof_stats"]["sample_size"] == 4
    assert msg["draft"][0]["shares"] == 100
    assert msg["draft"][0]["notional"] == 1000.0
    assert msg["bill"] == []
    assert msg["exits"] == []
    assert msg["calendar"] == []
    assert msg["opportunities"][0]["lot_size"] is None
    assert msg["opportunities"][0]["lot_step"] is None
    assert msg["opportunities"][0]["suggested_shares"] is None
    assert msg["opportunities"][0]["suggested_cash"] is None
    assert msg["opportunities"][0]["suggested_basis"] == ""
    assert msg["allocation_mode"] == ""
    assert msg["opportunities"][0]["status_tags"] == ["star_st"]
    assert msg["draft"][0]["status_tags"] == ["star_st"]


def test_session_snapshot_kelly_suggestion_and_lot():
    opp = SimpleNamespace(
        local_id=1,
        entity_id="000001.SZ",
        name="平安银行",
        entry_price_raw=10.0,
        ticker_stats=SimpleNamespace(
            sample_size=4,
            wins=3,
            win_rate=0.75,
            avg_roi=0.2,
        ),
    )
    engine = SimpleNamespace(
        dm_id="1",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="picking",
        is_completed=False,
        current_date="20250407",
        draft={},
        account=SimpleNamespace(
            cash=100_000.0,
            initial_cash=100_000.0,
            open_position_count=lambda: 0,
        ),
        allocation=SimpleNamespace(
            mode="kelly",
            max_portfolio_size=10,
            kelly_fraction=0.5,
            min_buy_shares=lambda _eid: 100,
            suggest_shares=lambda _account, _px, _eid, win_rate=None: 800,
        ),
        timeline=SimpleNamespace(asof_stats=lambda _d: None),
        opportunities=lambda: [opp],
        opportunity_by_local=lambda lid: opp if lid == 1 else None,
    )
    msg = session_snapshot(engine)
    assert msg["opportunities"][0]["lot_size"] == 100
    assert msg["opportunities"][0]["lot_step"] == 100
    assert msg["opportunities"][0]["suggested_shares"] == 800
    assert msg["opportunities"][0]["suggested_cash"] == 8000.0
    assert msg["opportunities"][0]["suggested_basis"] == "凯莉（胜率 75% × 折扣 0.5）"
    assert msg["allocation_mode"] == "kelly"


def test_session_snapshot_equal_capital_suggestion_without_asof():
    opp = SimpleNamespace(
        local_id=1,
        entity_id="000001.SZ",
        name="平安银行",
        entry_price_raw=10.0,
        ticker_stats=None,
    )
    engine = SimpleNamespace(
        dm_id="1",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="picking",
        is_completed=False,
        current_date="20230504",
        draft={},
        account=SimpleNamespace(
            cash=1_000_000.0,
            initial_cash=1_000_000.0,
            open_position_count=lambda: 0,
        ),
        allocation=SimpleNamespace(
            mode="equal_capital",
            max_portfolio_size=10,
            per_trade_capital=100_000.0,
            min_buy_shares=lambda _eid: 100,
            suggest_shares=lambda _account, _px, _eid, win_rate=None: 10_000,
        ),
        timeline=SimpleNamespace(asof_stats=lambda _d: None),
        opportunities=lambda: [opp],
        opportunity_by_local=lambda lid: opp if lid == 1 else None,
    )
    msg = session_snapshot(engine)
    assert msg["allocation_mode"] == "equal_capital"
    assert msg["opportunities"][0]["suggested_shares"] == 10_000
    assert msg["opportunities"][0]["suggested_cash"] == 100_000.0
    assert msg["opportunities"][0]["suggested_basis"] == "等价（每笔 100,000 元）"


def test_session_snapshot_equal_shares_suggestion():
    opp = SimpleNamespace(
        local_id=1,
        entity_id="000001.SZ",
        name="平安银行",
        entry_price_raw=10.0,
        ticker_stats=None,
    )
    engine = SimpleNamespace(
        dm_id="1",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="picking",
        is_completed=False,
        current_date="20230504",
        draft={},
        account=SimpleNamespace(
            cash=1_000_000.0,
            initial_cash=1_000_000.0,
            open_position_count=lambda: 0,
        ),
        allocation=SimpleNamespace(
            mode="equal_shares",
            max_portfolio_size=10,
            lots_per_trade=2,
            min_buy_shares=lambda _eid: 100,
            suggest_shares=lambda _account, _px, _eid, win_rate=None: 200,
        ),
        timeline=SimpleNamespace(asof_stats=lambda _d: None),
        opportunities=lambda: [opp],
        opportunity_by_local=lambda lid: opp if lid == 1 else None,
    )
    msg = session_snapshot(engine)
    assert msg["allocation_mode"] == "equal_shares"
    assert msg["opportunities"][0]["suggested_shares"] == 200
    assert msg["opportunities"][0]["suggested_cash"] == 2000.0
    assert msg["opportunities"][0]["suggested_basis"] == "等股（2 手）"


def test_session_snapshot_star_lot_step():
    opp = SimpleNamespace(
        local_id=1,
        entity_id="688981.SH",
        name="中芯国际",
        entry_price_raw=50.0,
        ticker_stats=None,
    )
    engine = SimpleNamespace(
        dm_id="1",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="picking",
        is_completed=False,
        current_date="20230504",
        draft={},
        account=SimpleNamespace(
            cash=1_000_000.0,
            initial_cash=1_000_000.0,
            open_position_count=lambda: 0,
        ),
        allocation=SimpleNamespace(
            mode="equal_shares",
            max_portfolio_size=10,
            lots_per_trade=1,
            min_buy_shares=lambda _eid: 200,
            lot_step_for_stock=lambda _eid: 1,
            suggest_shares=lambda _account, _px, _eid, win_rate=None: 200,
        ),
        timeline=SimpleNamespace(asof_stats=lambda _d: None),
        opportunities=lambda: [opp],
        opportunity_by_local=lambda lid: opp if lid == 1 else None,
    )
    msg = session_snapshot(engine)
    assert msg["opportunities"][0]["lot_size"] == 200
    assert msg["opportunities"][0]["lot_step"] == 1
    assert msg["opportunities"][0]["suggested_shares"] == 200
    assert msg["opportunities"][0]["suggested_cash"] == 10000.0


def test_session_snapshot_bill_when_confirming():
    opp = SimpleNamespace(
        local_id=2,
        entity_id="600000.SH",
        name="浦发",
        entry_price_raw=20.0,
        ticker_stats=None,
    )
    engine = SimpleNamespace(
        dm_id="2",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="confirming",
        is_completed=False,
        current_date="20250407",
        draft={2: 50},
        account=SimpleNamespace(
            cash=1.0,
            initial_cash=1.0,
            open_position_count=lambda: 0,
        ),
        allocation=SimpleNamespace(max_portfolio_size=5),
        timeline=SimpleNamespace(asof_stats=lambda _d: None),
        opportunities=lambda: [opp],
        opportunity_by_local=lambda lid: opp if lid == 2 else None,
    )
    msg = session_snapshot(engine)
    assert msg["phase"] == "confirming"
    assert msg["bill"][0]["shares"] == 50
    assert msg["opportunities"][0]["stats"] is None


def test_session_list_and_holdings_and_info():
    listed = session_list_message(
        {
            "version_id": "3",
            "strategy_key": "rsi_v1",
            "has_portfolio": True,
            "sessions": [
                {
                    "dm_id": "1",
                    "status": "in_progress",
                    "current_date": "20250407",
                    "updated_at": "t",
                }
            ],
        }
    )
    assert listed["has_portfolio"] is True
    assert listed["sessions"][0]["dm_id"] == "1"

    engine = SimpleNamespace(dm_id="1", current_date="20250407")
    row = SimpleNamespace(
        entity_id="000001.SZ",
        name="平安银行",
        status_tags=("st",),
        shares=100,
        buy_date="20250401",
        buy_price=10.0,
        hold_days=6,
        close=11.0,
        unrealized=100.0,
        goals=["止盈 win10%: +10.0%"],
    )
    held = holdings_message(engine, [row])
    assert held["holdings"][0]["unrealized"] == 100.0
    assert held["holdings"][0]["status_tags"] == ["st"]
    assert held["holdings"][0]["hold_unit"] == "natural_day"

    info = info_message(
        {
            "entity_id": "000001.SZ",
            "name": "平安银行",
            "status_tags": ["st"],
            "as_of": "20250407",
            "stats": {"sample_size": 1, "wins": 0, "win_rate": 0.0, "avg_roi": -0.1},
            "ticker_stats": {
                "sample_size": 0,
                "wins": 0,
                "win_rate": None,
                "avg_roi": None,
            },
            "columns": ["date", "open", "high", "low", "close", "rsi14"],
            "rows": [
                {
                    "date": "20250406",
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.5,
                    "close": 10.5,
                    "rsi14": float("nan"),
                },
                {
                    "date": "20250407",
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.5,
                    "close": 11.0,
                    "rsi14": 24.56,
                },
            ],
        }
    )
    assert info["ticker_stats"]["win_rate"] is None
    assert info["status_tags"] == ["st"]
    assert info["columns"][-1] == "rsi14"
    assert info["rows"][0]["rsi14"] is None
    assert info["candles"][-1]["date"] == "20250407"
    assert info["candles"][-1]["close"] == 11.0
    assert info["indicator_series"][0]["key"] == "rsi14"
    assert info["indicator_series"][0]["panel"] == "oscillator"
    assert info["indicator_series"][0]["data"] == [None, 24.56]
    json.dumps(info)


def test_session_snapshot_calendar_journal():
    engine = SimpleNamespace(
        dm_id="1",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="picking",
        is_completed=False,
        current_date="20240110",
        draft={},
        account=SimpleNamespace(
            cash=1_000_000.0,
            initial_cash=1_000_000.0,
            open_position_count=lambda: 0,
        ),
        allocation=None,
        timeline=SimpleNamespace(
            start_date="20240101",
            end_date="20240201",
            asof_stats=lambda _date: SimpleNamespace(to_dict=lambda: None),
        ),
        opportunities=lambda: [],
        opportunity_by_local=lambda _lid: None,
        calendar_journal=lambda: [
            {
                "date": "20240103",
                "opp_count": 2,
                "actions": [
                    {
                        "side": "buy",
                        "entity_id": "600000.SH",
                        "name": "浦发银行",
                        "shares": 1000,
                        "amount": 10_000.0,
                    }
                ],
            },
            {
                "date": "20240110",
                "opp_count": 0,
                "actions": [
                    {
                        "side": "sell",
                        "entity_id": "600000.SH",
                        "name": "浦发银行",
                        "shares": 1000,
                        "amount": 11_000.0,
                    }
                ],
            },
        ],
    )
    msg = session_snapshot(engine)
    assert msg["calendar"][0]["opp_count"] == 2
    assert msg["calendar"][0]["actions"][0]["side"] == "buy"
    assert msg["calendar"][1]["actions"][0]["amount"] == 11_000.0
