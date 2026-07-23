"""Scanner summary / cache-hit / tradability 标注。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from core.modules.strategy.core.engines.scanner.helpers.tradability import (
    annotate_buy_at_limit_up,
    opportunity_buy_at_limit_up,
)
from core.modules.strategy.core.engines.scanner.pipeline import ScannerPipeline
from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    StockInfo,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def _opp(
    stock_id: str,
    *,
    at_limit: bool | None = None,
) -> Opportunity:
    opp = Opportunity(
        stock=StockInfo(id=stock_id, name=stock_id),
        record_of_today={"date": "20240110", "close": 11.0, "pre_close": 10.0},
        trigger_date="20240110",
        trigger_price=11.0,
    )
    if at_limit is not None:
        opp.metadata["buy_at_limit_up"] = at_limit
    return opp


def test_calculate_summary_counts_limit_up() -> None:
    summary = ScannerPipeline.calculate_summary(
        [
            _opp("600000.SH", at_limit=True),
            _opp("600000.SH", at_limit=False),
            _opp("000001.SZ", at_limit=True),
        ]
    )
    assert summary["total_opportunities"] == 3
    assert summary["total_stocks"] == 2
    assert sorted(summary["stocks_with_opportunities"]) == ["000001.SZ", "600000.SH"]
    assert summary["at_limit_up_count"] == 2


def test_annotate_buy_at_limit_up_sets_metadata() -> None:
    opp = Opportunity(
        stock=StockInfo(id="600000.SH", name="x"),
        record_of_today={"date": "20240110", "close": 11.0, "pre_close": 10.0},
        trigger_date="20240110",
        trigger_price=11.0,
    )
    klines = [
        {
            "date": "20240110",
            "open": 11.0,
            "high": 11.0,
            "low": 11.0,
            "close": 11.0,
            "pre_close": 10.0,
        }
    ]
    annotate_buy_at_limit_up(
        opp,
        market_profile="china_a_stock",
        klines=klines,
        scan_date="20240110",
    )
    assert opportunity_buy_at_limit_up(opp) is True


def test_pipeline_cache_hit_skips_be(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "core.modules.strategy.core.engines.scanner.helpers.cache_manager.ProjectContext.path.get_strategy_scan_results_directory",
        lambda _name: tmp_path / "scan",
    )

    from core.modules.strategy.core.engines.scanner.helpers.cache_manager import (
        ScanCacheManager,
    )

    cache = ScanCacheManager("demo_key", max_cache_days=10)
    cache.save_opportunities("20240110", [_opp("600000.SH", at_limit=False)])

    class _Resolver:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def resolve_scan_date(self, *, use_strict: bool):
            _ = use_strict
            return "20240110", ["600000.SH", "000001.SZ"]

        def resolve_scan_date_with_meta(self, *, use_strict: bool):
            day, ids = self.resolve_scan_date(use_strict=use_strict)
            return (
                day,
                ids,
                {
                    "scan_date": day,
                    "use_strict": use_strict,
                    "mode": "strict" if use_strict else "non_strict",
                    "mode_label": "严格模式" if use_strict else "非严格模式",
                    "source_detail": "test fixture",
                },
            )

    monkeypatch.setattr(
        "core.modules.strategy.core.engines.scanner.pipeline.ScanDateResolver",
        _Resolver,
    )
    scan_stocks = MagicMock(return_value=[])
    monkeypatch.setattr(ScannerPipeline, "_scan_stocks", scan_stocks)
    monkeypatch.setattr(
        "core.modules.strategy.core.engines.scanner.pipeline.AdapterDispatcher.dispatch",
        lambda *a, **k: None,
    )

    settings = StrategySettings.from_dict(
        {
            "data": {"base": {"data_key": "stock.kline.daily", "params": {}}},
            "scanner": {"adapters": ["console"]},
            "simulation": {"execution": {"mode": "entity_based"}},
        }
    )
    info = SimpleNamespace(
        key="demo_key",
        unique_relative_path="demo/path",
        settings={},
        hooks_class=None,
        hooks_module_path="",
        strategy_file=Path("."),
    )
    # ScannerPipeline.run expects EnabledStrategyInfo-like; JobBuilder not called on cache hit
    report = ScannerPipeline.run(info, settings, force=False)  # type: ignore[arg-type]
    scan_stocks.assert_not_called()
    assert report["date"] == "20240110"
    assert report["total_opportunities"] == 1
    assert report["total_stocks"] == 2
