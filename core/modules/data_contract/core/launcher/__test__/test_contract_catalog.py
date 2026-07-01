"""contract_catalog list tests."""

from __future__ import annotations

from core.modules.data_contract.core.registry.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.core.launcher.contract_catalog import fetch_data_contract_catalog_page
from core.modules.data_contract.core.registry.mapping import default_map


def test_fetch_page_includes_core_keys():
    items, total = fetch_data_contract_catalog_page(page=1, limit=500)
    assert total >= len(default_map)
    keys = {item["key"] for item in items}
    assert DataKey.STOCK_LIST.value in keys


def test_summary_fields():
    items, _ = fetch_data_contract_catalog_page(page=1, limit=500)
    stock_list = next(i for i in items if i["key"] == DataKey.STOCK_LIST.value)
    assert stock_list["display_name"]
    assert stock_list["is_time_series"] is False
    assert stock_list["is_per_entity"] is False
    assert stock_list["origin"] == "system"
    assert stock_list["is_custom"] is False

    kline = next(i for i in items if i["key"] == DataKey.STOCK_KLINE_DAILY.value)
    assert kline["is_time_series"] is True
    assert kline["is_per_entity"] is True
    assert kline["origin"] == "system"


def test_summary_origin_labels():
    from core.modules.data_contract.core.launcher.contract_catalog import _summary

    system_row = _summary(
        DataKey.STOCK_LIST,
        default_map[DataKey.STOCK_LIST],
        "system",
    )
    assert system_row["origin"] == "system"
    assert system_row["is_custom"] is False

    custom_row = _summary(
        DataKey.STOCK_LIST,
        default_map[DataKey.STOCK_LIST],
        "userspace",
    )
    assert custom_row["origin"] == "userspace"
    assert custom_row["is_custom"] is True


def test_pagination():
    items, total = fetch_data_contract_catalog_page(page=1, limit=2)
    assert len(items) == min(2, total)
    if total > 2:
        page2, _ = fetch_data_contract_catalog_page(page=2, limit=2)
        assert page2[0]["key"] != items[0]["key"]
