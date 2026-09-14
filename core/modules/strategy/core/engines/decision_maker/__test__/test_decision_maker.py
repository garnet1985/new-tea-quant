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
from core.modules.strategy.core.engines.decision_maker.timeline import DecisionTimeline
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import Account, PortfolioEvent
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.shared.enum_result_contract.enum_result import (
    CompletedGoal,
    EnumResult,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run

_NAMES = {"600000.SH": "浦发银行", "000001.SZ": "平安银行"}


def _settings(**allocation) -> StrategySettings:
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


def _sell(date, entity, inv, *, roi=0.1, price=0.0):
    return PortfolioEvent(
        kind="sell",
        date=date,
        entity_id=entity,
        investment_id=inv,
        price=price,
        roi=roi,
        entry_price_raw=10.0,
    )


def _row(entity, inv, entry, exit_date, roi):
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
    )


def _engine(tmp_path: Path, events, rows=None, dm_id="1", **alloc):
    settings = _settings(**alloc)
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
        name_lookup=lambda eid: _NAMES.get(eid, ""),
        load_bars=lambda *a, **k: [],
        load_close=lambda *a, **k: 11.0,
        load_open_dates=lambda *a, **k: [],
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
    bill = engine.done()
    assert bill[0][1] == 200
    assert engine.phase == PHASE_CONFIRMING
    with pytest.raises(DecisionError, match="next"):
        engine.set_pick(1, 300)
    engine.reset()
    assert engine.draft == {}
    assert engine.current_date == "20240103"


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
    assert result.current_date == "20240115"
    assert len(result.logs) == 1
    assert result.logs[0].entity_id == "600000.SH"
    assert result.logs[0].profit == pytest.approx(1000)
    assert "win10%" in result.logs[0].goal_names
    assert engine.account.open_position_count() == 0
    assert engine.account.cash == pytest.approx(1_001_000)


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
    assert any("止盈" in g and "20240120" not in g for g in rows[0].goals)
    assert any("止损" in g for g in rows[0].goals)


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
