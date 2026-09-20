"""资金层日频盯市与夏普 / Sortino。"""

from __future__ import annotations

import math

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.portfolio.data_class import Account, Trade
from core.modules.strategy.core.engines.portfolio.report_manager.capital_metrics import (
    TRADING_DAYS_PER_YEAR,
    annualized_risk_ratios,
)
from core.modules.strategy.core.engines.portfolio.report_manager.daily_mtm import (
    hfq_close_from_bar,
    mark_portfolio_equity,
)
from core.modules.strategy.core.engines.portfolio.report_manager.overall_report import (
    OverallSummary,
)
from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimResult

DATES = [
    "20240102",
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


def _sim_with_round_trip(
    *,
    entry_hfq: float = 10.0,
    sell_roi: float = 0.2,
    shares: int = 1_000,
    buy_price: float = 10.0,
) -> PortfolioSimResult:
    buy = Trade.make_buy(
        date=DATES[0],
        entity_id="600000.SH",
        investment_id="a",
        shares=shares,
        price=buy_price,
        entry_price_hfq=entry_hfq,
    )
    sell = Trade.make_sell(
        date=DATES[7],
        entity_id="600000.SH",
        investment_id="a",
        shares=shares,
        buy_price=buy_price,
        roi=sell_roi,
    )
    return PortfolioSimResult(
        account=Account(initial_cash=100_000.0, cash=100_000.0),
        trades=[buy, sell],
    )


def test_hfq_close_from_bar_prefers_nested_hfq():
    assert hfq_close_from_bar({"hfq": {"close": 12.5}, "raw": {"close": 6.0}, "adj_factor": 2.0}) == 12.5
    assert hfq_close_from_bar({"raw": {"close": 5.0}, "adj_factor": 2.0}) == pytest.approx(10.0)
    assert hfq_close_from_bar({"hfq": {"close": 0}}) is None


def test_daily_mtm_marks_hfq_roi_and_drops_sold_name():
    hfq = {
        DATES[0]: 10.0,
        DATES[1]: 11.0,
        # DATES[2] 缺 bar → 沿用 11
        DATES[3]: 12.0,
        DATES[4]: 12.0,
        DATES[5]: 12.0,
        DATES[6]: 12.0,
        DATES[7]: 12.0,
        DATES[8]: 99.0,  # 已清仓，不应进市值
        DATES[9]: 99.0,
    }

    def load_closes(entity_id: str, start: str, end: str):
        assert entity_id == "600000.SH"
        assert start == DATES[0]
        assert end == DATES[7]
        return dict(hfq)

    sim = mark_portfolio_equity(
        _sim_with_round_trip(sell_roi=0.2),
        start_date=DATES[0],
        end_date=DATES[9],
        load_open_dates=lambda *_: list(DATES),
        load_hfq_closes=load_closes,
    )
    assert sim.equity_marked_to_market is True
    assert [p["date"] for p in sim.equity_curve] == DATES

    by_date = {p["date"]: p for p in sim.equity_curve}
    # 买入 1000×10，现金 90_000；d0 fill→收盘 ROI=0
    assert by_date[DATES[0]]["cash"] == pytest.approx(90_000.0)
    assert by_date[DATES[0]]["equity"] == pytest.approx(100_000.0)
    assert by_date[DATES[0]]["open_positions"] == 1
    # d1 hfq 11 → 90_000 + 1000×10×1.1
    assert by_date[DATES[1]]["equity"] == pytest.approx(101_000.0)
    # 缺 K 沿用昨收
    assert by_date[DATES[2]]["equity"] == pytest.approx(101_000.0)
    assert by_date[DATES[3]]["equity"] == pytest.approx(102_000.0)
    # 卖出日：先成交再标剩余；ROI 0.2 → 现金 102_000，持仓 0
    assert by_date[DATES[7]]["cash"] == pytest.approx(102_000.0)
    assert by_date[DATES[7]]["equity"] == pytest.approx(102_000.0)
    assert by_date[DATES[7]]["open_positions"] == 0
    assert by_date[DATES[8]]["equity"] == pytest.approx(102_000.0)
    assert by_date[DATES[8]]["open_positions"] == 0


def test_bonus_share_does_not_halve_nav():
    """10 送 10：raw 腰斩、hfq 不动 → 净值不应腰斩。"""
    hfq = {d: 10.0 for d in DATES}

    sim = mark_portfolio_equity(
        _sim_with_round_trip(entry_hfq=10.0, sell_roi=0.0),
        start_date=DATES[0],
        end_date=DATES[9],
        load_open_dates=lambda *_: list(DATES),
        load_hfq_closes=lambda *_: dict(hfq),
    )
    held = [p for p in sim.equity_curve if p["open_positions"] == 1]
    assert held
    for point in held:
        assert point["equity"] == pytest.approx(100_000.0)


def test_open_position_final_equity_includes_unrealized():
    buy = Trade.make_buy(
        date=DATES[0],
        entity_id="600000.SH",
        investment_id="a",
        shares=1_000,
        price=10.0,
        entry_price_hfq=10.0,
    )
    prices = [10.0, 11.0, 12.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 19.0]
    hfq = {d: px for d, px in zip(DATES, prices)}
    sim = mark_portfolio_equity(
        PortfolioSimResult(
            account=Account(initial_cash=100_000.0, cash=90_000.0),
            trades=[buy],
        ),
        start_date=DATES[0],
        end_date=DATES[9],
        load_open_dates=lambda *_: list(DATES),
        load_hfq_closes=lambda *_: dict(hfq),
    )
    last = sim.equity_curve[-1]
    # 期末 hfq = 10 + 9 = 19 → 90_000 + 1000×10×1.9
    assert last["equity"] == pytest.approx(109_000.0)
    assert last["open_positions"] == 1
    summary = OverallSummary.build_from_sim(sim, shibor_overnight={})
    assert summary.final_total_equity == pytest.approx(109_000.0)
    assert summary.total_return == pytest.approx(0.09)
    assert summary.sharpe_ratio is not None
    assert summary.sortino_ratio is not None


def test_empty_calendar_keeps_cost_curve():
    sim = _sim_with_round_trip()
    sim.equity_curve = [
        {"date": DATES[0], "cash": 90_000.0, "equity": 100_000.0, "open_positions": 1}
    ]
    out = mark_portfolio_equity(
        sim,
        start_date=DATES[0],
        end_date=DATES[9],
        load_open_dates=lambda *_: [],
        load_hfq_closes=lambda *_: {"x": 1.0},
    )
    assert out.equity_marked_to_market is False
    assert len(out.equity_curve) == 1
    summary = OverallSummary.build_from_sim(out, shibor_overnight={})
    assert summary.sharpe_ratio is None
    assert summary.sortino_ratio is None


def test_annualized_risk_ratios_formula_and_insufficient_samples():
    values = [100.0, 101.0, 99.0, 102.0]
    r = [
        (101.0 - 100.0) / 100.0,
        (99.0 - 101.0) / 101.0,
        (102.0 - 99.0) / 99.0,
    ]
    mean = sum(r) / 3.0
    var = sum((x - mean) ** 2 for x in r) / 2.0
    std = math.sqrt(var)
    down = math.sqrt(sum(min(x, 0.0) ** 2 for x in r) / 3.0)
    scale = math.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe, sortino = annualized_risk_ratios(values)
    assert sharpe == pytest.approx(mean / std * scale)
    assert sortino == pytest.approx(mean / down * scale)

    assert annualized_risk_ratios([100.0]) == (None, None)
    assert annualized_risk_ratios([100.0, 100.0, 100.0]) == (None, None)
    # 从未亏损：Sortino 分母为 0
    up_only = [100.0, 101.0, 102.0, 103.0]
    sharpe_up, sortino_up = annualized_risk_ratios(up_only)
    assert sharpe_up is not None
    assert sortino_up is None


def test_overnight_shibor_lowers_sharpe_vs_rf_zero():
    from core.modules.strategy.core.engines.portfolio.report_manager.risk_free import (
        annual_pct_to_daily,
        overnight_daily_rf,
    )

    values = [100.0, 101.0, 99.0, 102.0]
    sharpe0, _ = annualized_risk_ratios(values, rf_daily=0.0)
    rf = annual_pct_to_daily(1.5)
    sharpe_rf, sortino_rf = annualized_risk_ratios(values, rf_daily=rf)
    assert sharpe0 is not None and sharpe_rf is not None
    assert sharpe_rf < sharpe0
    assert sortino_rf is not None

    dates = DATES[:4]
    series = overnight_daily_rf(dates, {DATES[0]: 1.5, DATES[2]: 1.5})
    assert len(series) == 3
    assert series[0] == pytest.approx(rf)
    assert series[1] == pytest.approx(rf)  # 缺 DATES[1] 沿用


def test_overall_summary_uses_injected_shibor():
    buy = Trade.make_buy(
        date=DATES[0],
        entity_id="600000.SH",
        investment_id="a",
        shares=1_000,
        price=10.0,
        entry_price_hfq=10.0,
    )
    prices = [10.0, 11.0, 12.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 19.0]
    sim = mark_portfolio_equity(
        PortfolioSimResult(
            account=Account(initial_cash=100_000.0, cash=90_000.0),
            trades=[buy],
        ),
        start_date=DATES[0],
        end_date=DATES[9],
        load_open_dates=lambda *_: list(DATES),
        load_hfq_closes=lambda *_: {d: px for d, px in zip(DATES, prices)},
    )
    zero = OverallSummary.build_from_sim(sim, shibor_overnight={})
    with_rf = OverallSummary.build_from_sim(
        sim, shibor_overnight={d: 1.5 for d in DATES}
    )
    assert zero.sharpe_ratio is not None and with_rf.sharpe_ratio is not None
    assert with_rf.sharpe_ratio < zero.sharpe_ratio


def test_report_manager_finalize_writes_daily_mtm_curve(tmp_path):
    from core.modules.strategy.core.engines.portfolio.report_manager import ReportManager

    hfq = {d: 10.0 for d in DATES}
    sim = _sim_with_round_trip(sell_roi=0.0)
    report = ReportManager(
        output_dir=tmp_path / "1",
        strategy_key="demo",
        strategy_path="demo/rsi",
        version_id=1,
        enum_version_id="3",
    ).finalize(
        sim,
        period={"start_date": DATES[0], "end_date": DATES[9]},
        load_open_dates=lambda *_: list(DATES),
        load_hfq_closes=lambda *_: dict(hfq),
        load_shibor_overnight=lambda *_: {},
    )
    assert len(report["summary"]["equity_curve_labels"]) >= 2
    assert report["summary"]["final_total_equity"] == pytest.approx(100_000.0)
    assert report["capitalMetrics"]["sharpeRatio"] is None  # 净值全平，波动为 0
    curve_path = tmp_path / "1" / "equity_curve.json"
    assert curve_path.is_file()
    import json

    written = json.loads(curve_path.read_text(encoding="utf-8"))
    assert len(written) == len(DATES)
    assert written[0]["date"] == DATES[0]
    assert written[-1]["open_positions"] == 0
