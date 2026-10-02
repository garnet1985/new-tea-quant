"""组合层诊断：买到 / 漏掉、槽位、分组。"""
from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from core.modules.strategy.core.engines.analyzer.steps.layer import LayerPipeline
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    PriceFactorStore,
    PriceInvestmentRow,
)
from core.modules.strategy.core.services.artifacts.io import ArtifactIO
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_store_cache():
    ArtifactStore.clear_cache()
    yield
    ArtifactStore.clear_cache()


def _price_row(
    opportunity_id: str,
    *,
    roi: float,
    enter_date: str = "20230102",
    exit_reason: str = "take_profit",
) -> PriceInvestmentRow:
    return PriceInvestmentRow(
        opportunity_id=opportunity_id,
        enter_date=enter_date,
        enter_price=10.0,
        enter_price_hfq=10.0,
        exit_date="20230120",
        roi=roi,
        holding_days=12,
        exit_reason=exit_reason,
        skip_reason="",
        lifecycle="complete",
        result="win" if roi > 0 else "loss",
    )


def _enum_row(
    entity_id: str,
    investment_id: str,
    *,
    rsi: float,
    weighted_roi: float,
) -> EnumResult:
    return EnumResult(
        entity_id=entity_id,
        investment_id=investment_id,
        trigger_date="20230101",
        lifecycle="complete",
        entry_date="20230101",
        exit_reason="take_profit" if weighted_roi >= 0 else "stop_loss",
        weighted_roi=weighted_roi,
        holding_days=5,
        result="win" if weighted_roi >= 0 else "loss",
        signal_snapshot={"rsi": rsi},
    )


def _buy(entity_id: str, investment_id: str) -> dict:
    return {
        "date": "20230102",
        "entity_id": entity_id,
        "investment_id": investment_id,
        "side": "buy",
        "shares": 100,
        "price": 10.0,
        "amount": 1000.0,
        "fees": 0.0,
        "entry_price_hfq": 10.0,
    }


def _write_enum(enum_dir: Path, rows_by_entity: dict[str, list[EnumResult]]) -> None:
    enum_dir.mkdir(parents=True, exist_ok=True)
    manager = EnumResultsManager.at(enum_dir)
    for eid, rows in rows_by_entity.items():
        manager.accept(eid, rows)
    manager.persist()


def _portfolio_store(
    tmp_path: Path,
    *,
    book: dict[str, list[PriceInvestmentRow]],
    buys: list[tuple[str, str]],
    enum_rows: dict[str, list[EnumResult]] | None = None,
    slots: int = 10,
    peak_open: int = 10,
    util_avg: float = 25.0,
    util_peak: float = 93.0,
    top5_pct: float = 40.0,
    max_drawdown: float = 0.12,
    equity_curve: list[dict] | None = None,
    write_price: bool = True,
) -> ArtifactStore:
    version_dir = tmp_path / "simulations" / "1"
    portfolio_dir = version_dir / "portfolio"
    portfolio_dir.mkdir(parents=True)
    if write_price:
        price_dir = version_dir / "price"
        price_dir.mkdir(parents=True, exist_ok=True)
        ids = list(book)
        writer = PriceFactorStore.at(price_dir, version_id="1")
        writer.entity_ids = ids
        for eid, rows in book.items():
            writer.write_investments(eid, rows)
    if enum_rows is not None:
        _write_enum(version_dir / "enum", enum_rows)
    ArtifactIO.write_json(portfolio_dir / "trades.json", [_buy(e, i) for e, i in buys])
    ArtifactIO.write_json(
        portfolio_dir / "overall_report.json",
        {
            "strategy_key": "demo",
            "version_id": 1,
            "summary": {
                "buy_trades": len(buys),
                "completed_investments": len(buys),
                "total_return": 0.08,
                "win_rate": 0.5,
                "average_open_positions": 3.5,
                "peak_open_positions": peak_open,
                "capital_utilization_ratio_pct": util_avg,
                "peak_capital_utilization_ratio_pct": util_peak,
                "full_exposure_days_ratio_pct": 16.0,
                "max_drawdown": max_drawdown,
                "top5_profit_concentration_pct": top5_pct,
            },
        },
    )
    ArtifactIO.write_json(
        portfolio_dir / "equity_curve.json",
        equity_curve
        or [
            {"date": "20230101", "equity": 100000.0, "open_positions": 2},
            {"date": "20230601", "equity": 120000.0, "open_positions": peak_open},
            {"date": "20230701", "equity": 90000.0, "open_positions": peak_open},
        ],
    )
    VersionMetaStore.write_effective_settings(
        tmp_path / "simulations",
        "1",
        {
            "portfolio": {
                "allocation": {
                    "mode": "equal_capital",
                    "max_portfolio_size": slots,
                    "max_weight_per_stock": 0.3,
                    "skip_trade_when_insufficient": True,
                }
            }
        },
    )
    return ArtifactStore.hydrate(
        portfolio_dir, kind=SimulateKind.PORTFOLIO, version_id="1"
    )


def test_portfolio_layer_leftover_better_and_slots_cap(tmp_path, capsys):
    book = {
        "AAA.SH": [_price_row("1", roi=0.01), _price_row("2", roi=0.02)],
        "BBB.SH": [
            _price_row("3", roi=0.10),
            _price_row("4", roi=0.12),
            _price_row("5", roi=0.08),
        ],
    }
    store = _portfolio_store(
        tmp_path,
        book=book,
        buys=[("AAA.SH", "1"), ("AAA.SH", "2")],
        peak_open=10,
        slots=10,
        util_avg=25.0,
    )
    report = LayerPipeline.run(store, present=True, force=True)
    assert report["layer"] == "portfolio"
    fill = report["facts"]["fill"]
    assert fill["price_completed"] == 5
    assert fill["taken_count"] == 2
    assert fill["leftover_count"] == 3
    assert fill["slots_at_cap"] is True
    quality = report["facts"]["taken_vs_leftover"]
    assert quality["roi_gap"] > 0
    ids = {item["id"] for item in report["conclusions"]}
    assert "fill_gap" in ids
    assert "leftover_better" in ids
    assert "slots_at_cap" in ids
    assert "cash_idle" in ids
    assert "not_price_edge" in ids
    suggestions = {item["id"]: item for item in report["suggestions"]}
    assert suggestions["leftover_better"]["needs_overlay"] is True
    assert "+2" not in suggestions["leftover_better"]["text"]
    assert "2%" not in suggestions["leftover_better"]["text"]
    printed = capsys.readouterr().out
    assert "组合层归因" in printed
    assert "事实" in printed
    assert "漏掉" in printed


def test_portfolio_layer_leftover_worse_does_not_blame_slots(tmp_path):
    book = {
        "AAA.SH": [_price_row("1", roi=0.10), _price_row("2", roi=0.12)],
        "BBB.SH": [_price_row("3", roi=-0.04), _price_row("4", roi=-0.06)],
    }
    store = _portfolio_store(
        tmp_path,
        book=book,
        buys=[("AAA.SH", "1"), ("AAA.SH", "2")],
        peak_open=4,
        slots=10,
        util_avg=80.0,
    )
    report = LayerPipeline.run(store, present=False, force=True)
    ids = {item["id"] for item in report["conclusions"]}
    assert "leftover_worse" in ids
    assert "slots_at_cap" not in ids
    assert "leftover_better" not in ids


def test_portfolio_layer_without_price_does_not_invent_leftover(tmp_path):
    store = _portfolio_store(
        tmp_path,
        book={},
        buys=[("AAA.SH", "1")],
        write_price=False,
    )
    report = LayerPipeline.run(store, present=False, force=True)
    assert report["facts"]["price_available"] is False
    ids = {item["id"] for item in report["conclusions"]}
    assert "no_price_contrast" in ids
    assert "leftover_better" not in ids
    suggestion_ids = {item["id"] for item in report["suggestions"]}
    assert "no_price_contrast" in suggestion_ids


def test_portfolio_layer_rsi_grouping_mismatch(tmp_path):
    book = {
        "AAA.SH": [
            _price_row("1", roi=0.01),
            _price_row("2", roi=0.02),
            _price_row("3", roi=0.00),
        ],
        "BBB.SH": [
            _price_row("4", roi=0.12),
            _price_row("5", roi=0.10),
            _price_row("6", roi=0.11),
        ],
    }
    enum_rows = {
        "AAA.SH": [
            _enum_row("AAA.SH", "1", rsi=22.0, weighted_roi=0.01),
            _enum_row("AAA.SH", "2", rsi=21.0, weighted_roi=0.02),
            _enum_row("AAA.SH", "3", rsi=25.0, weighted_roi=0.00),
        ],
        "BBB.SH": [
            _enum_row("BBB.SH", "4", rsi=12.0, weighted_roi=0.12),
            _enum_row("BBB.SH", "5", rsi=11.0, weighted_roi=0.10),
            _enum_row("BBB.SH", "6", rsi=10.0, weighted_roi=0.11),
        ],
    }
    store = _portfolio_store(
        tmp_path,
        book=book,
        buys=[("AAA.SH", "1"), ("AAA.SH", "2"), ("AAA.SH", "3")],
        enum_rows=enum_rows,
        peak_open=3,
        slots=10,
        util_avg=70.0,
    )
    report = LayerPipeline.run(store, present=False, force=True)
    rsi_groups = {
        item["name"]: item
        for item in report["facts"]["groups"]
        if item["kind"] == "rsi"
    }
    assert rsi_groups["RSI<15"]["taken_count"] == 0
    assert rsi_groups["RSI≥20"]["taken_count"] == 3
    ids = {item["id"] for item in report["conclusions"]}
    assert "grouping_mismatch" in ids


def test_portfolio_presenter_three_blocks():
    from core.modules.strategy.core.engines.analyzer.steps.layer.present import (
        LayerPresenter,
    )

    stream = StringIO()
    LayerPresenter(
        {
            "layer": "portfolio",
            "version_id": "4",
            "disclaimer": "资金约束后的账户成交",
            "facts": {
                "price_available": True,
                "allocation": {"mode": "equal_capital", "max_portfolio_size": 10},
                "fill": {
                    "price_completed": 124,
                    "taken_count": 48,
                    "leftover_count": 76,
                    "fill_ratio": 0.387,
                    "total_return": 0.08,
                    "win_rate": 0.5,
                    "avg_open_positions": 3.5,
                    "peak_open_positions": 10,
                    "max_portfolio_size": 10,
                    "slots_at_cap": True,
                    "capital_utilization_ratio_pct": 25.0,
                    "peak_capital_utilization_ratio_pct": 93.0,
                    "full_exposure_days_ratio_pct": 16.0,
                    "top5_profit_concentration_pct": 40.0,
                },
                "taken_vs_leftover": {
                    "taken": {"avg_roi": 0.02},
                    "leftover": {"avg_roi": 0.06},
                    "roi_gap": 0.04,
                },
                "groups": [
                    {
                        "kind": "rsi",
                        "name": "RSI<15",
                        "price_avg_roi": 0.08,
                        "taken_count": 2,
                    }
                ],
            },
            "conclusions": [{"id": "x", "text": "漏掉的更好"}],
            "suggestions": [{"id": "y", "text": "有对照格再改槽位"}],
        }
    ).present(stream)
    text = stream.getvalue()
    assert "组合层归因" in text
    assert "事实" in text
    assert "漏掉的更好" in text
    assert "有对照格再改槽位" in text
    assert "2500" not in text
