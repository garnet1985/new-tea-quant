"""价格层诊断：去噪账边、利润头部、合并偏。"""
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

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_store_cache():
    ArtifactStore.clear_cache()
    yield
    ArtifactStore.clear_cache()


def _enum_row(
    entity_id: str,
    investment_id: str,
    *,
    weighted_roi: float,
    trigger_date: str = "20230101",
) -> EnumResult:
    return EnumResult(
        entity_id=entity_id,
        investment_id=investment_id,
        trigger_date=trigger_date,
        lifecycle="complete",
        entry_date=trigger_date,
        exit_reason="take_profit" if weighted_roi >= 0 else "stop_loss",
        weighted_roi=weighted_roi,
        holding_days=5,
        result="win" if weighted_roi >= 0 else "loss",
    )


def _price_row(
    opportunity_id: str,
    *,
    roi: float,
    enter_date: str = "20230102",
    exit_reason: str = "take_profit",
    skip_reason: str = "",
) -> PriceInvestmentRow:
    skipped = bool(skip_reason)
    return PriceInvestmentRow(
        opportunity_id=opportunity_id,
        enter_date="" if skipped else enter_date,
        enter_price=10.0,
        enter_price_hfq=10.0,
        exit_date="" if skipped else "20230120",
        roi=0.0 if skipped else roi,
        holding_days=0 if skipped else 12,
        exit_reason="" if skipped else exit_reason,
        skip_reason=skip_reason,
        lifecycle="skipped" if skipped else "complete",
        result="" if skipped else ("win" if roi > 0 else "loss"),
    )


def _write_enum(enum_dir: Path, rows_by_entity: dict[str, list[EnumResult]]) -> None:
    enum_dir.mkdir(parents=True, exist_ok=True)
    manager = EnumResultsManager.at(enum_dir)
    for eid, rows in rows_by_entity.items():
        manager.accept(eid, rows)
    manager.persist()


def _price_store(
    tmp_path: Path,
    rows_by_entity: dict[str, list[PriceInvestmentRow]],
    *,
    enum_rows: dict[str, list[EnumResult]] | None = None,
) -> ArtifactStore:
    version_dir = tmp_path / "simulations" / "1"
    price_dir = version_dir / "price"
    price_dir.mkdir(parents=True)
    if enum_rows is not None:
        _write_enum(version_dir / "enum", enum_rows)
    ids = list(rows_by_entity)
    store = ArtifactStore.hydrate(
        price_dir,
        kind=SimulateKind.PRICE_FACTOR,
        version_id="1",
        entity_ids=ids,
        start_date="20230101",
        end_date="20241231",
        strategy_key="demo",
    )
    writer = PriceFactorStore.at(price_dir, version_id="1")
    writer.entity_ids = ids
    for eid, rows in rows_by_entity.items():
        writer.write_investments(eid, rows)
    return store


def test_price_layer_has_edge_and_keeps_chapter_when_counts_match(tmp_path, capsys):
    rows = {
        "AAA.SH": [
            _price_row(str(i), roi=0.03, enter_date=f"202301{i:02d}")
            for i in range(1, 13)
        ]
    }
    enum_rows = {
        "AAA.SH": [
            _enum_row("AAA.SH", str(i), weighted_roi=0.03, trigger_date=f"202301{i:02d}")
            for i in range(1, 13)
        ]
    }
    store = _price_store(tmp_path, rows, enum_rows=enum_rows)
    report = LayerPipeline.run(store, present=True, force=True)
    assert report["layer"] == "price_factor"
    assert report["facts"]["book"]["completed_count"] == 12
    assert report["facts"]["book"]["avg_roi"] == pytest.approx(0.03)
    assert report["facts"]["denoising"]["merged_count"] == 0
    ids = {item["id"] for item in report["conclusions"]}
    assert "has_edge" in ids
    assert "denoising_neutral" in ids
    assert "not_account_return" in ids
    assert "few_opportunities" not in ids
    printed = capsys.readouterr().out
    assert "价格层归因" in printed
    assert "事实" in printed
    assert "等权机会账" in printed


def test_price_layer_profit_fragile_and_merged_worse(tmp_path):
    book = [_price_row("1", roi=0.50, exit_reason="take_profit")]
    book.extend(
        [
            _price_row(str(i), roi=-0.02, enter_date=f"202302{i:02d}", exit_reason="stop_loss")
            for i in range(2, 9)
        ]
    )
    enum_rows = {
        "AAA.SH": [
            _enum_row("AAA.SH", "1", weighted_roi=0.50),
            *[
                _enum_row("AAA.SH", str(i), weighted_roi=-0.02, trigger_date=f"202302{i:02d}")
                for i in range(2, 9)
            ],
            _enum_row("AAA.SH", "99", weighted_roi=-0.20, trigger_date="20230210"),
        ]
    }
    store = _price_store(tmp_path, {"AAA.SH": book}, enum_rows=enum_rows)
    report = LayerPipeline.run(store, present=False, force=True)
    facts = report["facts"]
    assert facts["book"]["avg_roi"] > 0
    assert facts["concentration"]["still_positive_without_top5_trades"] is False
    assert facts["denoising"]["merged_count"] == 1
    assert facts["denoising"]["merged_mean_roi"] == pytest.approx(-0.20)
    ids = {item["id"] for item in report["conclusions"]}
    assert "profit_concentrated" in ids
    assert "profit_fragile" in ids
    assert "merged_worse" in ids
    assert "exit_mix" in ids


def test_price_layer_limit_up_skip_and_yearly_flip(tmp_path):
    rows = {
        "AAA.SH": [
            *[_price_row(str(i), roi=-0.04, enter_date=f"202301{i:02d}") for i in range(1, 5)],
            *[_price_row(str(i), roi=0.05, enter_date=f"202401{i:02d}") for i in range(5, 9)],
            _price_row("9", roi=0.0, skip_reason="buy_at_limit_up"),
        ]
    }
    enum_rows = {
        "AAA.SH": [
            *[_enum_row("AAA.SH", str(i), weighted_roi=-0.04) for i in range(1, 5)],
            *[_enum_row("AAA.SH", str(i), weighted_roi=0.05) for i in range(5, 9)],
            _enum_row("AAA.SH", "9", weighted_roi=0.10, trigger_date="20240109"),
        ]
    }
    store = _price_store(tmp_path, rows, enum_rows=enum_rows)
    report = LayerPipeline.run(store, present=False, force=True)
    years = {item["year"]: item for item in report["facts"]["yearly"]}
    assert years["2023"]["avg_roi"] < 0
    assert years["2024"]["avg_roi"] > 0
    assert report["facts"]["denoising"]["skipped_buy_at_limit_up"] == 1
    ids = {item["id"] for item in report["conclusions"]}
    assert "yearly_unstable" in ids
    assert "tradability_skip" in ids


def test_price_layer_without_enum_does_not_invent_merge_bias(tmp_path):
    store = _price_store(
        tmp_path,
        {"AAA.SH": [_price_row("1", roi=0.04)]},
    )
    report = LayerPipeline.run(store, present=False, force=True)
    assert report["facts"]["denoising"]["enum_available"] is False
    ids = {item["id"] for item in report["conclusions"]}
    assert "no_enum_contrast" in ids
    assert "merged_worse" not in ids
    suggestion_ids = {item["id"] for item in report["suggestions"]}
    assert "no_enum_contrast" in suggestion_ids


def test_price_presenter_three_blocks():
    from core.modules.strategy.core.engines.analyzer.steps.layer.present import (
        LayerPresenter,
    )

    stream = StringIO()
    LayerPresenter(
        {
            "layer": "price_factor",
            "version_id": "4",
            "disclaimer": "等权机会账",
            "facts": {
                "book": {
                    "completed_count": 12,
                    "win_rate": 0.58,
                    "avg_roi": 0.032,
                    "profit_factor": 1.8,
                },
                "concentration": {
                    "top5_trades_profit_share": 0.4,
                    "avg_roi_without_top5_trades": 0.01,
                },
                "exits": {
                    "by_reason": [
                        {
                            "reason": "take_profit",
                            "label": "止盈",
                            "count": 7,
                            "profit_share": 1.4,
                        }
                    ]
                },
                "yearly": [{"year": "2023", "avg_roi": 0.02}],
                "denoising": {
                    "enum_available": True,
                    "enum_count": 18,
                    "price_book_count": 12,
                    "merged_count": 5,
                    "skipped_buy_at_limit_up": 1,
                },
            },
            "conclusions": [{"id": "x", "text": "去噪账有边"}],
            "suggestions": [{"id": "y", "text": "不要先改仓位"}],
        }
    ).present(stream)
    text = stream.getvalue()
    assert "价格层归因" in text
    assert "事实" in text
    assert "去噪账有边" in text
    assert "不要先改仓位" in text
