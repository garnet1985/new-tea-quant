"""Strategy.scan Facade 契约（可在 refactor freeze 下跑）。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.strategy import Strategy

pytestmark = pytest.mark.force_run


def test_strategy_scan_empty_targets() -> None:
    with patch.object(Strategy, "_resolve_scan_targets", return_value=[]):
        assert Strategy.scan() == {}


def test_strategy_scan_calls_pipeline() -> None:
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
    with patch.object(Strategy, "_resolve_scan_targets", return_value=[info]):
        with patch(
            "core.modules.strategy.core.engines.scanner.helpers.ScanDateResolver.load_kline_latest_date",
            return_value="20240110",
        ):
            with patch(
                "core.modules.strategy.core.engines.scanner.ScannerPipeline.run",
                return_value=fake_report,
            ) as run:
                out = Strategy.scan("demo", demo=True)
    assert out == {"demo": fake_report}
    run.assert_called_once()
