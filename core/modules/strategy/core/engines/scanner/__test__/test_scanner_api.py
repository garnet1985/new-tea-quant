"""Strategy.scan Facade 契约（委托 ScannerPipeline.scan）。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.strategy import Strategy
from core.modules.strategy.core.engines.scanner import ScannerPipeline

pytestmark = pytest.mark.force_run


def test_strategy_scan_delegates_to_pipeline() -> None:
    with patch.object(ScannerPipeline, "scan", return_value={}) as scan:
        assert Strategy.scan("demo", demo=True) == {}
    scan.assert_called_once_with("demo", demo=True)


def test_scanner_pipeline_scan_empty_targets() -> None:
    with patch.object(ScannerPipeline, "resolve_targets", return_value=[]):
        assert ScannerPipeline.scan() == {}


def test_scanner_pipeline_scan_calls_run() -> None:
    fake_report = {
        "date": "20240110",
        "total_opportunities": 0,
        "total_stocks": 0,
        "summary": {
            "total_opportunities": 0,
            "total_stocks": 0,
            "stocks_with_opportunities": [],
            "at_limit_up_count": 0,
        },
    }
    info = type(
        "Info",
        (),
        {
            "key": "demo",
            "unique_relative_path": "demo",
            "settings": {
                "data": {"base": {"data_key": "stock.kline.daily"}},
                "scanner": {"use_strict_previous_trading_day": False},
                "simulation": {"execution": {"mode": "entity_based"}},
            },
            "is_enabled": True,
        },
    )()
    with patch.object(ScannerPipeline, "resolve_targets", return_value=[info]):
        with patch(
            "core.modules.strategy.core.engines.scanner.pipeline.ScanDateResolver.load_kline_latest_date",
            return_value="20240110",
        ):
            with patch.object(ScannerPipeline, "run", return_value=fake_report) as run:
                out = ScannerPipeline.scan("demo", demo=True)
    assert out == {"demo": fake_report}
    run.assert_called_once()


def test_scanner_pipeline_scan_strict_gate_raises() -> None:
    """非 demo：严格交易日门闸阻塞时应直接 ValueError，不进入 run。"""
    info = type(
        "Info",
        (),
        {
            "key": "demo",
            "unique_relative_path": "demo",
            "settings": {},
            "is_enabled": True,
        },
    )()
    with patch.object(ScannerPipeline, "resolve_targets", return_value=[info]):
        with patch(
            "core.modules.strategy.core.engines.scanner.pipeline.ScanDateResolver.strict_data_block_reason",
            return_value="calendar not aligned",
        ):
            with patch.object(ScannerPipeline, "run") as run:
                with pytest.raises(ValueError, match="calendar not aligned"):
                    ScannerPipeline.scan("demo", demo=False)
    run.assert_not_called()
