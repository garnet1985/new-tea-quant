"""real_world_trading_date helpers."""
from unittest.mock import patch

import pytest

from core.modules.data_source.core.service import real_world_trading_date as mod

pytestmark = pytest.mark.force_run


def test_latest_completed_skips_today():
    with patch.object(mod.Utils.date, "today", return_value="20250521"):
        out = mod._latest_completed(["20250520", "20250521"])
    assert out == "20250520"


def test_fetch_uses_akshare():
    with patch.object(mod, "_try_fetch", return_value="20250519") as try_fetch:
        out = mod.fetch_real_world_latest_completed_trading_date()
    assert out == ("20250519", "akshare")
    try_fetch.assert_called_once()


def test_fetch_returns_none_when_all_fail():
    with patch.object(mod, "_try_fetch", return_value=None):
        assert mod.fetch_real_world_latest_completed_trading_date() is None
