"""ScanDateResolver 严格 / 非严格截止日。"""
from unittest.mock import MagicMock, patch

from core.modules.strategy.engines.scanner.helpers.date_resolver import ScanDateResolver


def test_resolve_anchor_date_strict_uses_real_world():
    cal = MagicMock()
    cal.get_real_world_latest_completed_trading_date.return_value = "20250523"
    cal.get_latest_completed_trading_date.return_value = "20250520"
    dm = MagicMock()
    dm.service.calendar = cal

    assert ScanDateResolver.resolve_anchor_date(dm, use_strict=True) == "20250523"
    cal.get_real_world_latest_completed_trading_date.assert_called_once()
    cal.get_latest_completed_trading_date.assert_not_called()


def test_resolve_anchor_date_non_strict_uses_freshness_end_date():
    cal = MagicMock()
    cal.get_real_world_latest_completed_trading_date.return_value = "20250523"
    dm = MagicMock()
    dm.service.calendar = cal
    dm.stock.kline.load_latest_date.return_value = "20250520"

    with patch(
        "core.modules.data_source.catalog.freshness_probe._resolve_freshness_end_date",
        return_value="20250520",
    ) as resolve_end:
        assert ScanDateResolver.resolve_anchor_date(dm, use_strict=False) == "20250520"
        resolve_end.assert_called_once_with(dm)
    cal.get_real_world_latest_completed_trading_date.assert_not_called()


def test_resolve_anchor_date_non_strict_clamps_when_calendar_ahead_of_kline():
    dm = MagicMock()
    dm.stock.kline.load_latest_date.return_value = "20251231"

    with patch(
        "core.modules.data_source.catalog.freshness_probe._resolve_freshness_end_date",
        return_value="20260101",
    ):
        assert ScanDateResolver.resolve_anchor_date(dm, use_strict=False) == "20251231"


def test_resolve_scan_date_routes_by_mode():
    resolver = ScanDateResolver(MagicMock())
    with patch.object(
        resolver, "_resolve_strict_date", return_value=("20250523", ["000001.SZ"])
    ) as strict, patch.object(
        resolver, "_resolve_non_strict_date", return_value=("20250520", ["000001.SZ"])
    ) as relaxed:
        assert resolver.resolve_scan_date(use_strict=True) == ("20250523", ["000001.SZ"])
        assert resolver.resolve_scan_date(use_strict=False) == ("20250520", ["000001.SZ"])
        strict.assert_called_once()
        relaxed.assert_called_once()
