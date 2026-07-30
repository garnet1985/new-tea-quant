"""contract_catalog list tests."""

from __future__ import annotations

from core.modules.data_contract.core.data_contracts.data_keys import SYS_DATA_KEY
from core.modules.data_contract.launcher.contract_catalog import fetch_data_contract_catalog_page


def test_fetch_page_includes_core_keys():
    items, total = fetch_data_contract_catalog_page(page=1, limit=500)
    assert total >= 1
    keys = {item["key"] for item in items}
    assert SYS_DATA_KEY.STOCK_LIST in keys


def test_summary_fields():
    items, _ = fetch_data_contract_catalog_page(page=1, limit=500)
    stock_list = next(i for i in items if i["key"] == SYS_DATA_KEY.STOCK_LIST)
    assert stock_list["display_name"]
    assert stock_list["is_time_series"] is False
    assert stock_list["is_per_entity"] is False
    assert stock_list["origin"] == "system"
    assert stock_list["is_custom"] is False

    kline = next(i for i in items if i["key"] == SYS_DATA_KEY.STOCK_KLINE_DAILY)
    assert kline["is_time_series"] is True
    assert kline["is_per_entity"] is True
    assert kline["origin"] == "system"


def test_pagination():
    items, total = fetch_data_contract_catalog_page(page=1, limit=2)
    assert len(items) == min(2, total)
    if total > 2:
        page2, _ = fetch_data_contract_catalog_page(page=2, limit=2)
        assert page2[0]["key"] != items[0]["key"]
