"""real_world_trading_date helpers."""
from unittest.mock import patch

import pytest

from core.modules.data_source.core.service import real_world_trading_date as mod

pytestmark = pytest.mark.force_run


def test_extract_eastmoney_skips_today():
    with patch.object(mod.Utils.date, "today", return_value="20250521"):
        out = mod._extract_latest_date_from_klines(
            ["2025-05-20,1", "2025-05-21,2"],
            is_eastmoney=True,
        )
    assert out == "20250520"


def test_fetch_prefers_sina():
    with patch.object(mod, "_try_fetch", side_effect=["20250519", None]) as try_fetch:
        out = mod.fetch_real_world_latest_completed_trading_date()
    assert out == ("20250519", "sina")
    assert try_fetch.call_count == 1


def test_fetch_falls_through_to_eastmoney():
    with patch.object(mod, "_try_fetch", side_effect=[None, "20250518"]):
        out = mod.fetch_real_world_latest_completed_trading_date()
    assert out == ("20250518", "eastmoney")


def test_fetch_returns_none_when_all_fail():
    with patch.object(mod, "_try_fetch", return_value=None):
        assert mod.fetch_real_world_latest_completed_trading_date() is None
