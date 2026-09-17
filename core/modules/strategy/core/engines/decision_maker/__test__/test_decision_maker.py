"""决策者会话引擎 / 存档 / as-of（不连 DuckDB）。"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from core.modules.market_profile import MarketRulesProxy
from core.modules.strategy.core.engines.decision_maker.broker import DecisionBroker
from core.modules.strategy.core.engines.decision_maker.engine import (
    PHASE_CONFIRMING,
    AmbiguousSessionsError,
    DecisionEngine,
    DecisionError,
)
from core.modules.strategy.core.engines.decision_maker.info import parse_info_args
from core.modules.strategy.core.engines.decision_maker.repl import DecisionRepl
from core.modules.strategy.core.engines.decision_maker.store import (
    STATUS_IN_PROGRESS,
    DecisionStore,
)
from core.modules.strategy.core.engines.decision_maker.timeline import (
    DecisionTimeline,
    lot_key,
)
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import (
    Account,
    PortfolioEvent,
    Position,
)
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.portfolio.simulator import OpenLot
from core.modules.strategy.core.engines.shared.enum_result_contract.enum_result import (
    CompletedGoal,
    EnumResult,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run

_NAMES = {"600000.SH": "浦发银行", "000001.SZ": "平安银行"}


def _settings(expiration=None, take_profit=None, **allocation) -> StrategySettings:
    raw = {
        "portfolio": {
            "initial_capital": 1_000_000,
            "allocation": {
                "mode": "equal_capital",
                "max_portfolio_size": 10,
                "lots_per_trade": 1,
                "kelly_fraction": 0.5,
                "skip_trade_when_insufficient": False,
            },
            "output": {"save_trades": True, "save_equity_curve": True},
        },
        "fees": {
            "commission_rate": 0.0,
            "min_commission": 0.0,
            "stamp_duty_rate": 0.0,
            "transfer_fee_rate": 0.0,
        },
        "goal": {
            "take_profit": {
                "stages": [{"ratio": 0.1, "name": "win10%", "close_invest": True}]
            },
            "stop_loss": {
                "stages": [{"ratio": -0.05, "name": "loss5%", "close_invest": True}]
            },
        },
    }
    if expiration:
        raw["goal"]["expiration"] = expiration
    if take_profit is not None:
        raw["goal"]["take_profit"] = take_profit
    if allocation:
        raw["portfolio"]["allocation"].update(allocation)
    settings = StrategySettings.from_dict(raw)
    settings.apply_defaults()
    return settings


def _allocation(**kwargs) -> AllocationStrategy:
    settings = _settings(**kwargs)
    return AllocationStrategy.create(
        settings=settings,
        market_rules=MarketRulesProxy.for_market("china_a_stock"),
        fee_calculator=FeeCalculator(
            commission_rate=0.0,
            min_commission=0.0,
            stamp_duty_rate=0.0,
            transfer_fee_rate=0.0,
        ),
    )


def _buy(date, entity, inv, price, *, volume=None, hfq=None, roi=0.0):
    return PortfolioEvent(
        kind="buy",
        date=date,
        entity_id=entity,
        investment_id=inv,
        price=price,
        entry_price_raw=price,
        entry_price_hfq=float(hfq if hfq is not None else price),
        bar_volume=volume,
    )


def _sell(date, entity, inv, *, roi=0.1, price=0.0, exit_ratio=1.0, goal_name=""):
    return PortfolioEvent(
        kind="sell",
        date=date,
        entity_id=entity,
        investment_id=inv,
        price=price,
        roi=roi,
        entry_price_raw=10.0,
        exit_ratio=exit_ratio,
        goal_name=goal_name,
    )


def _row(entity, inv, entry, exit_date, roi, **extra):
    return EnumResult(
        entity_id=entity,
        investment_id=inv,
        entry_date=entry,
        entry_price_raw=10.0,
        exit_date=exit_date,
        weighted_roi=roi,
        completed_goals=(
            CompletedGoal(name="win10%", date=exit_date, reason="take_profit"),
        ),
        **extra,
    )


def _engine(
    tmp_path: Path,
    events,
    rows=None,
    dm_id="1",
    name_lookup=None,
    expiration=None,
    open_dates=None,
    load_bars=None,
    load_close=None,
    take_profit=None,
    **alloc,
):
    settings = _settings(expiration=expiration, take_profit=take_profit, **alloc)
    allocation = _allocation(**alloc)
    timeline = DecisionTimeline.from_events(
        events,
        rows=rows or (),
        start_date="20240101",
        end_date="20240201",
    )
    store = DecisionStore.at(tmp_path / "3")
    return DecisionEngine.from_parts(
        store=store,
        dm_id=dm_id,
        timeline=timeline,
        settings=settings,
        allocation=allocation,
        strategy_key="demo",
        version_id="3",
        name_lookup=name_lookup or (lambda eid: _NAMES.get(eid, "")),
        load_bars=load_bars or (lambda *a, **k: []),
        load_close=load_close if load_close is not None else (lambda *a, **k: 11.0),
        load_open_dates=lambda *a, **k: list(open_dates or []),
        load_hfq_closes=lambda *a, **k: {},
        load_shibor_overnight=lambda *a, **k: {},
    )


def test_pauses_on_first_buy_date(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _sell("20240110", "600000.SH", "a"),
            _buy("20240115", "000001.SZ", "b", 20.0),
        ],
    )
    assert engine.current_date == "20240103"
    opps = engine.opportunities()
    assert [o.entity_id for o in opps] == ["600000.SH"]
    assert opps[0].name == "浦发银行"


def test_opportunity_uses_enum_status_and_bare_name(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [_buy("20240103", "300108.SZ", "a", 10.0)],
        rows=[
            _row(
                "300108.SZ",
                "a",
                "20240103",
                "20240120",
                0.1,
                stock_name="吉药",
                stock_status_at_trigger=("star_st",),
            )
        ],
        name_lookup=lambda eid: "*ST吉药(退)",
    )
    opps = engine.opportunities()
    assert opps[0].name == "吉药"
    assert opps[0].status_tags == ("star_st",)


def test_opportunity_strips_lookup_name_when_enum_name_missing(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [_buy("20240103", "300108.SZ", "a", 10.0)],
        name_lookup=lambda eid: "*ST吉药(退)",
    )
    opps = engine.opportunities()
    assert opps[0].name == "吉药"
    assert opps[0].status_tags == ()


def test_asof_stats_exclude_future_exits(tmp_path: Path):
    rows = [
        _row("600000.SH", "a", "20240103", "20240110", 0.1),
        _row("000001.SZ", "b", "20240115", "20240120", -0.2),
    ]
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _sell("20240110", "600000.SH", "a"),
            _buy("20240115", "000001.SZ", "b", 20.0),
            _sell("20240120", "000001.SZ", "b", roi=-0.2),
        ],
        rows=rows,
    )
    early = engine.timeline.asof_stats("20240103")
    assert early.sample_size == 0
    later = engine.timeline.asof_stats("20240115")
    assert later.sample_size == 1
    assert later.wins == 1
    assert later.avg_roi == pytest.approx(0.1)


def test_asof_stats_skip_open_lifecycle(tmp_path: Path):
    """持仓未归零（仍 open）的枚举不计胜率。"""
    rows = [
        _row("600000.SH", "done", "20240103", "20240110", 0.1, lifecycle="complete"),
        _row("600000.SH", "live", "20240103", "20240120", 0.9, lifecycle="open"),
    ]
    engine = _engine(
        tmp_path,
        [_buy("20240103", "600000.SH", "done", 10.0)],
        rows=rows,
    )
    stats = engine.timeline.asof_stats("20240115")
    assert stats.sample_size == 1
    assert stats.avg_roi == pytest.approx(0.1)


def test_asof_stats_ticker_completed_before_decision_day(tmp_path: Path):
    """D 日机会的胜率 / ROI = 该标的 exit_date < D 的已完成枚举，不含未来、不含其他票。"""
    rows = [
        _row("000488.SZ", "old1", "20230110", "2023-02-01", 0.10),
        _row("000488.SZ", "old2", "20230301", "20230401", -0.05),
        EnumResult(
            entity_id="000488.SZ",
            investment_id="",
            entry_date="20230120",
            exit_date="20230210",
            weighted_roi=0.20,
        ),
        _row("000488.SZ", "open", "20230504", "20230601", 0.99),
        _row("600000.SH", "other", "20230115", "20230215", 0.50),
    ]
    engine = _engine(
        tmp_path,
        [_buy("20230504", "000488.SZ", "open", 1.92)],
        rows=rows,
    )
    opps = engine.opportunities()
    assert len(opps) == 1
    stats = opps[0].ticker_stats
    assert stats is not None
    assert stats.sample_size == 3
    assert stats.wins == 2
    assert stats.win_rate == pytest.approx(2.0 / 3.0)
    assert stats.avg_roi == pytest.approx((0.10 - 0.05 + 0.20) / 3.0)


def test_opportunity_list_uses_per_ticker_asof(tmp_path: Path):
    rows = [
        _row("600000.SH", "a1", "20240102", "20240105", 0.10),
        _row("600000.SH", "a2", "20240102", "20240105", -0.05),
        _row("000001.SZ", "b1", "20240102", "20240105", -0.20),
    ]
    engine = _engine(
        tmp_path,
        [
            _buy("20240110", "600000.SH", "c", 10.0),
            _buy("20240110", "000001.SZ", "d", 20.0),
        ],
        rows=rows,
    )
    opps = engine.opportunities()
    assert [o.entity_id for o in opps] == ["000001.SZ", "600000.SH"]
    ping = next(o for o in opps if o.entity_id == "000001.SZ")
    pu = next(o for o in opps if o.entity_id == "600000.SH")
    assert ping.ticker_stats is not None
    assert ping.ticker_stats.sample_size == 1
    assert ping.ticker_stats.win_rate == pytest.approx(0.0)
    assert ping.ticker_stats.avg_roi == pytest.approx(-0.20)
    assert pu.ticker_stats is not None
    assert pu.ticker_stats.sample_size == 2
    assert pu.ticker_stats.win_rate == pytest.approx(0.5)
    assert pu.ticker_stats.avg_roi == pytest.approx(0.025)
    assert ping.stats is not None and pu.stats is not None
    assert ping.stats.sample_size == pu.stats.sample_size == 3

    stdout = StringIO()
    DecisionRepl(engine, stdin=StringIO("quit\n"), stdout=stdout).run()
    text = stdout.getvalue()
    assert "000001.SZ" in text and "历史胜率: 0%" in text and "平均ROI: -20.0%" in text
    assert "600000.SH" in text and "历史胜率: 50%" in text and "平均ROI: +2.5%" in text


def test_pick_done_reset_and_lot_error(tmp_path: Path):
    engine = _engine(
        tmp_path, [_buy("20240103", "600000.SH", "a", 10.0)]
    )
    with pytest.raises(DecisionError, match="手数"):
        engine.set_pick(1, 50)
    with pytest.raises(DecisionError, match="没有编号"):
        engine.set_pick(9, 100)
    opp, shares, notional = engine.set_pick(1, 1000)
    assert shares == 1000
    assert notional == pytest.approx(10_000)
    engine.set_pick(1, 200)
    engine.set_pick(1, 0)
    assert engine.draft == {}
    engine.set_pick(1, 200)
    bill = engine.done()
    assert bill[0][1] == 200
    assert engine.phase == PHASE_CONFIRMING
    with pytest.raises(DecisionError, match="next"):
        engine.set_pick(1, 300)
    engine.reset()
    assert engine.draft == {}
    assert engine.current_date == "20240103"


def test_set_pick_cash_floors_to_lot(tmp_path: Path):
    engine = _engine(tmp_path, [_buy("20240103", "600000.SH", "a", 10.0)])
    with pytest.raises(DecisionError, match="一手"):
        engine.set_pick_cash(1, 50)
    opp, shares, notional = engine.set_pick_cash(1, 10_050)
    assert opp.entity_id == "600000.SH"
    assert shares == 1000
    assert notional == pytest.approx(10_000)


def test_next_requires_done_empty_means_skip(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _sell("20240110", "600000.SH", "a"),
            _buy("20240115", "000001.SZ", "b", 20.0),
        ],
        rows=[_row("600000.SH", "a", "20240103", "20240110", 0.1)],
    )
    with pytest.raises(DecisionError, match="done"):
        engine.next()
    engine.done()
    result = engine.next()
    assert result.completed is False
    assert result.current_date == "20240115"
    assert result.logs == []
    assert engine.account.cash == pytest.approx(1_000_000)
    assert engine.account.open_position_count() == 0


def test_buy_then_exit_log_then_next_decision(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _sell("20240110", "600000.SH", "a", roi=0.1),
            _buy("20240115", "000001.SZ", "b", 20.0),
        ],
        rows=[_row("600000.SH", "a", "20240103", "20240110", 0.1)],
    )
    engine.set_pick(1, 1000)
    engine.done()
    result = engine.next()
    assert result.completed is False
    assert result.current_date == "20240110"
    assert result.opportunities == []
    assert len(result.logs) == 1
    assert result.logs[0].entity_id == "600000.SH"
    assert result.logs[0].profit == pytest.approx(1000)
    assert "win10%" in result.logs[0].goal_names
    assert engine.account.open_position_count() == 0
    assert engine.account.cash == pytest.approx(1_001_000)
    engine.done()
    nxt = engine.next()
    assert nxt.completed is False
    assert nxt.current_date == "20240115"
    assert nxt.logs == []
    assert [o.entity_id for o in nxt.opportunities] == ["000001.SZ"]


def test_partial_take_profit_marks_stage_and_labels_event(tmp_path: Path):
    row = EnumResult(
        entity_id="600000.SH",
        investment_id="a",
        entry_date="20240103",
        entry_price_raw=10.0,
        exit_date="20240120",
        weighted_roi=0.25,
        completed_goals=(
            CompletedGoal(
                name="win15%",
                date="20240110",
                reason="take_profit",
                exit_ratio=0.3,
                roi=0.15,
            ),
            CompletedGoal(
                name="win25%",
                date="20240120",
                reason="take_profit",
                exit_ratio=0.7,
                roi=0.25,
            ),
        ),
    )
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0, hfq=10.0),
            _sell(
                "20240110",
                "600000.SH",
                "a",
                roi=0.15,
                exit_ratio=0.3,
                goal_name="win15%",
            ),
            _sell(
                "20240120",
                "600000.SH",
                "a",
                roi=0.25,
                exit_ratio=0.7,
                goal_name="win25%",
            ),
        ],
        rows=[row],
        take_profit={
            "stages": [
                {"ratio": 0.15, "exit_ratio": 0.3},
                {"ratio": 0.25, "close_invest": True},
            ]
        },
    )
    engine.set_pick(1, 1000)
    engine.done()
    result = engine.next()
    assert result.current_date == "20240110"
    assert result.logs[0].goal_names == "win15%"
    assert result.logs[0].reason == "take_profit"
    held = engine.holdings()[0]
    assert held.shares == 700
    assert any(g.done and "win15%" in g.text for g in held.goals)
    assert any((not g.done) and "win25%" in g.text for g in held.goals)


def test_calendar_journal_records_opps_and_fills(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _sell("20240110", "600000.SH", "a", roi=0.1),
            _buy("20240115", "000001.SZ", "b", 20.0),
        ],
        rows=[_row("600000.SH", "a", "20240103", "20240110", 0.1)],
    )
    by_date = {row["date"]: row for row in engine.calendar_journal()}
    assert by_date["20240103"]["opp_count"] == 1
    assert by_date["20240103"]["actions"] == []
    assert "20240115" not in by_date
    engine.set_pick(1, 1000)
    engine.done()
    engine.next()
    by_date = {row["date"]: row for row in engine.calendar_journal()}
    buys = [row for row in by_date["20240103"]["actions"] if row["side"] == "buy"]
    assert buys[0]["shares"] == 1000
    assert buys[0]["amount"] == pytest.approx(10_000)
    assert buys[0]["name"] == "浦发银行"
    sells = [row for row in by_date["20240110"]["actions"] if row["side"] == "sell"]
    assert sells[0]["shares"] == 1000
    assert sells[0]["amount"] == pytest.approx(11_000)
    assert by_date["20240110"]["opp_count"] == 0
    assert "20240115" not in by_date
    engine.done()
    engine.next()
    by_date = {row["date"]: row for row in engine.calendar_journal()}
    assert by_date["20240115"]["opp_count"] == 1
    assert by_date["20240115"]["actions"] == []


def test_same_day_settles_exits_before_new_buys(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _sell("20240110", "600000.SH", "a", roi=0.1),
            _buy("20240110", "000001.SZ", "b", 20.0),
        ],
        rows=[_row("600000.SH", "a", "20240103", "20240110", 0.1)],
    )
    engine.set_pick(1, 1000)
    engine.done()
    result = engine.next()
    assert result.current_date == "20240110"
    assert len(result.logs) == 1
    assert [o.entity_id for o in result.opportunities] == ["000001.SZ"]
    assert engine.account.open_position_count() == 0


def test_max_portfolio_size(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _buy("20240103", "000001.SZ", "b", 20.0),
        ],
        max_portfolio_size=1,
    )
    engine.set_pick(1, 100)
    with pytest.raises(DecisionError, match="组合上限"):
        engine.set_pick(2, 100)


def test_cash_rejected_at_pick(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [_buy("20240103", "600000.SH", "a", 10.0)],
    )
    engine.account.cash = 50
    with pytest.raises(DecisionError, match="现金"):
        engine.set_pick(1, 100)


def test_complete_writes_report_without_overwriting_id(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0),
            _sell("20240110", "600000.SH", "a"),
        ],
        rows=[_row("600000.SH", "a", "20240103", "20240110", 0.1)],
    )
    engine.set_pick(1, 100)
    engine.done()
    paused = engine.next()
    assert paused.completed is False
    assert paused.current_date == "20240110"
    engine.done()
    result = engine.next()
    assert result.completed is True
    session_dir = engine.store.session_dir("1")
    assert (session_dir / "session.json").is_file()
    assert engine.store.get_index("1")["status"] != STATUS_IN_PROGRESS
    second = engine.store.allocate_id()
    assert second == "2"
    assert engine.store.exists("1")


def test_attach_ambiguous_unfinished(tmp_path: Path):
    store = DecisionStore.at(tmp_path / "3")
    a = store.allocate_id()
    b = store.allocate_id()
    store.save_session(a, {"status": STATUS_IN_PROGRESS, "current_date": "20240103"})
    store.save_session(b, {"status": STATUS_IN_PROGRESS, "current_date": "20240104"})
    with pytest.raises(AmbiguousSessionsError):
        DecisionEngine._pick_session(store, session_id=None, new_session=False)
    assert DecisionEngine._pick_session(store, session_id=None, new_session=True) == "3"
    assert DecisionEngine._pick_session(store, session_id="1", new_session=False) == "1"


def test_same_entity_one_opportunity_per_day(tmp_path: Path):
    events = [
        _buy("20240103", "000001.SZ", "1", 12.0),
        _buy("20240103", "600000.SH", "12", 10.0),
        _buy("20240103", "600000.SH", "13", 10.0),
    ]
    engine = _engine(tmp_path, events)
    opps = engine.opportunities()
    assert [(o.local_id, o.entity_id, o.investment_id) for o in opps] == [
        (1, "000001.SZ", "1"),
        (2, "600000.SH", "12"),
    ]


def test_skips_buy_day_when_already_holding_same_entity(tmp_path: Path):
    events = [
        _buy("20240103", "600000.SH", "a", 10.0),
        _buy("20240110", "600000.SH", "b", 10.0),
        _sell("20240120", "600000.SH", "a", roi=0.1),
        _sell("20240125", "600000.SH", "b", roi=0.05),
    ]
    engine = _engine(tmp_path, events, dm_id="hold")
    engine.set_pick(1, 100)
    engine.done()
    result = engine.next()
    assert result.completed is False
    assert result.current_date == "20240120"
    assert result.opportunities == []
    assert [item.entity_id for item in result.logs] == ["600000.SH"]
    engine.done()
    done = engine.next()
    assert done.completed is True
    assert done.current_date != "20240110"


def test_resume_same_id_after_quit(tmp_path: Path):
    events = [_buy("20240103", "600000.SH", "a", 10.0)]
    engine = _engine(tmp_path, events)
    engine.set_pick(1, 200)
    engine.save()
    again = _engine(tmp_path, events, dm_id="1")
    assert again.draft[1] == 200
    assert again.current_date == "20240103"


def test_holdings_show_declared_goals_not_future_date(tmp_path: Path):
    held = _engine(
        tmp_path,
        [_buy("20240103", "600000.SH", "a", 10.0, hfq=10.0)],
        dm_id="9",
    )
    held.set_pick(1, 100)
    held.done()
    held._commit_draft()
    rows = held.holdings()
    assert len(rows) == 1
    assert rows[0].shares == 100
    assert rows[0].status_tags == ()
    assert any("止盈" in g.text and "20240120" not in g.text for g in rows[0].goals)
    assert any("止损" in g.text for g in rows[0].goals)
    assert all("→" not in g.text for g in rows[0].goals)
    assert all(g.done is False for g in rows[0].goals)


def test_holdings_trading_day_span_matches_expiration_unit(tmp_path: Path):
    open_dates = [
        "20240103",
        "20240104",
        "20240105",
        "20240108",
        "20240109",
        "20240110",
        "20240111",
        "20240112",
        "20240115",
    ]
    engine = _engine(
        tmp_path,
        [
            _buy("20240103", "600000.SH", "a", 10.0, hfq=10.0),
            _buy("20240115", "000001.SZ", "b", 20.0),
        ],
        expiration={"fixed_window_in_days": 30, "mode": "trading_day"},
        open_dates=open_dates,
    )
    engine.set_pick(1, 100)
    engine.done()
    engine.next()
    rows = engine.holdings()
    assert engine.current_date == "20240115"
    assert rows[0].hold_days == 9
    assert rows[0].hold_unit == "trading_day"
    assert any("到期 30 个交易日" in g.text for g in rows[0].goals)


def test_holdings_roi_uses_hfq_not_qfq_over_raw(tmp_path: Path):
    bars = [
        {
            "date": "20240103",
            "close": 19.13,
            "raw": {"close": 15.11},
            "hfq": {"close": 11.0},
        }
    ]
    engine = _engine(
        tmp_path,
        [_buy("20240103", "600000.SH", "a", 10.0, hfq=10.0)],
        load_bars=lambda *a, **k: bars,
        load_close=lambda *a, **k: 19.13,
    )
    engine.set_pick(1, 100)
    engine.done()
    engine._commit_draft()
    row = engine.holdings()[0]
    assert row.close == pytest.approx(19.13)
    assert row.roi == pytest.approx(0.10)
    assert row.unrealized == pytest.approx(100.0)
    assert row.market_value == pytest.approx(1100.0)
    mixed = (19.13 - 10.0) / 10.0
    assert abs(row.roi - mixed) > 0.5


def test_holdings_without_hfq_does_not_mark_print_spread(tmp_path: Path):
    engine = _engine(
        tmp_path,
        [_buy("20240103", "600000.SH", "a", 10.0, hfq=10.0)],
    )
    engine.set_pick(1, 100)
    engine.done()
    engine._commit_draft()
    row = engine.holdings()[0]
    assert row.close == pytest.approx(11.0)
    assert row.roi is None
    assert row.unrealized is None
    assert row.market_value is None


def test_info_arg_parse():
    target, n, keep = parse_info_args(["1"])
    assert target == "1" and n == 60 and keep is None
    target, n, keep = parse_info_args(["1", "120"])
    assert n == 120
    target, n, keep = parse_info_args(["1", "close,rsi"])
    assert n == 60 and keep == ["close", "rsi"]
    target, n, keep = parse_info_args(["000001.SZ", "120", "close,rsi"])
    assert target == "000001.SZ" and n == 120 and keep == ["close", "rsi"]
    target, n, keep = parse_info_args(["1", "999"])
    assert n == 252


def test_repl_pick_and_quit(tmp_path: Path):
    engine = _engine(
        tmp_path, [_buy("20240103", "600000.SH", "a", 10.0)]
    )
    stdin = StringIO("1:100\ndone\nquit\n")
    stdout = StringIO()
    code = DecisionRepl(engine, stdin=stdin, stdout=stdout).run()
    assert code == 0
    text = stdout.getvalue()
    assert "已选择" in text
    assert "当前选择" in text
    assert "已存档" in text
    assert engine.draft[1] == 100


def test_broker_rejects_non_lot():
    alloc = _allocation()
    broker = DecisionBroker(allocation=alloc, fee_calculator=alloc.fee_calculator)
    preview, err = broker.preview_buy(
        _buy("20240103", "600000.SH", "a", 10.0),
        50,
        Account(initial_cash=1_000_000, cash=1_000_000),
        {},
    )
    assert preview is None
    assert err is not None
    assert "手数" in err.message


def test_broker_sell_floors_to_lot_until_last():
    """中间卖出向下取整到 100 股；最后一笔把剩余零股清掉。"""
    alloc = _allocation()
    broker = DecisionBroker(allocation=alloc, fee_calculator=alloc.fee_calculator)
    account = Account(initial_cash=1_000_000, cash=480_000)
    account.positions["000488.SZ"] = Position(
        entity_id="000488.SZ",
        shares=52_000,
        average_cost=10.0,
        current_investment_id="a",
    )
    lots = {
        lot_key("000488.SZ", "a"): OpenLot(
            investment_id="a",
            entity_id="000488.SZ",
            shares=52_000,
            buy_price=10.0,
            buy_date="20250227",
            initial_shares=52_000,
        )
    }
    mid = PortfolioEvent(
        kind="sell",
        date="20250410",
        entity_id="000488.SZ",
        investment_id="a",
        price=9.5,
        roi=-0.05,
        exit_ratio=8194 / 52_000,
    )
    trade, skip = broker.apply_sell(mid, account, lots, is_last=False)
    assert skip is None
    assert trade is not None
    assert trade.shares == 8100
    assert account.positions["000488.SZ"].shares == 43_900

    last = PortfolioEvent(
        kind="sell",
        date="20250411",
        entity_id="000488.SZ",
        investment_id="a",
        price=9.4,
        roi=-0.06,
        exit_ratio=0.15,
    )
    trade2, skip2 = broker.apply_sell(last, account, lots, is_last=True)
    assert skip2 is None
    assert trade2 is not None
    assert trade2.shares == 43_900
    assert "000488.SZ" not in account.positions
