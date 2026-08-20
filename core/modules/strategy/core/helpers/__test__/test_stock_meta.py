"""StockMetaHelper：ProcessPool suspend 期间不得打开主库。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper

pytestmark = pytest.mark.force_run


def test_load_returns_fallback_when_pool_suspended() -> None:
    with patch.object(StockMetaHelper, "_duckdb_pool_suspended", return_value=True):
        with patch(
            "core.modules.data_manager.DataManager",
            side_effect=AssertionError("must not open DataManager while suspended"),
        ):
            out = StockMetaHelper.load("600000.SH")
    assert out["id"] == "600000.SH"
    assert out["name"] == "600000.SH"


def test_load_map_skips_db_when_pool_suspended() -> None:
    with patch.object(StockMetaHelper, "_duckdb_pool_suspended", return_value=True):
        with patch(
            "core.modules.data_manager.DataManager",
            side_effect=AssertionError("must not open DataManager while suspended"),
        ):
            out = StockMetaHelper.load_map(["a", "b"])
    assert set(out) == {"a", "b"}
    assert out["a"]["id"] == "a"


def test_from_payload_prefers_cached_stock_info() -> None:
    with patch.object(
        StockMetaHelper,
        "load_map",
        side_effect=AssertionError("must use payload cache"),
    ):
        out = StockMetaHelper.from_payload(
            {
                "stock_info": {
                    "600000.SH": {
                        "id": "600000.SH",
                        "name": "浦发银行",
                        "delist_date": "",
                    }
                }
            },
            ["600000.SH"],
        )
    assert out["600000.SH"]["name"] == "浦发银行"


def test_load_map_uses_load_all_once() -> None:
    list_svc = MagicMock()
    list_svc.load_all.return_value = [
        {
            "id": "600000.SH",
            "name": "浦发银行",
            "delist_date": "0",
            "industry": "银行",
        }
    ]
    list_svc._normalize_delist_date = lambda raw: None if str(raw) in ("0", "0.0") else raw
    dm = MagicMock()
    dm.stock.list = list_svc

    with patch.object(StockMetaHelper, "_duckdb_pool_suspended", return_value=False):
        with patch(
            "core.modules.data_manager.DataManager",
            return_value=dm,
        ):
            out = StockMetaHelper.load_map(["600000.SH", "missing"])
    list_svc.load_all.assert_called_once()
    assert out["600000.SH"]["name"] == "浦发银行"
    assert out["600000.SH"]["delist_date"] == ""
    assert out["missing"]["name"] == "missing"
