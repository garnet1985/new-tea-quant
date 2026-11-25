"""申万行业读取。"""
from __future__ import annotations

from core.modules.data_manager.core.data_services.industry.sw_industry_service import (
    SW_A_SHARE_ID,
    SwIndustryService,
)


class _Table:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    def load(self, condition="1=1", params=(), order_by=None, limit=None, offset=None):
        self.calls.append((condition, tuple(params), order_by))
        rows = list(self.rows)
        if condition == "level = %s" and params:
            rows = [row for row in rows if row.get("level") == params[0]]
        return rows


class _Manager:
    def __init__(self, tables):
        self.tables = tables

    def get_table(self, name):
        return self.tables.get(name)


def _service():
    tables = {
        "sys_data_sw_industry": _Table(
            [
                {"id": "801010.SI", "industry_code": "110000", "name": "农林牧渔", "level": "L1"},
                {"id": "801011.SI", "industry_code": "110100", "name": "种植业", "level": "L2"},
            ]
        ),
        "sys_map_sw_stock_industry": _Table(
            [
                {
                    "stock_id": "000001.SZ",
                    "l1_code": "801010.SI",
                    "l2_code": "801011.SI",
                    "l3_code": "801012.SI",
                    "in_date": "20210101",
                }
            ]
        ),
        "sys_data_sw_industry_kline": _Table(
            [{"id": "801010.SI", "date": "20240102", "close": 1.0}]
        ),
    }
    return SwIndustryService(_Manager(tables)), tables


def test_quote_list_adds_sw_a_share():
    svc, _ = _service()
    rows = svc.load_quote_list()
    ids = [row["id"] for row in rows]
    assert ids == ["801010.SI", SW_A_SHARE_ID]


def test_quote_list_does_not_duplicate_sw_a_share():
    svc, tables = _service()
    tables["sys_data_sw_industry"].rows.append(
        {"id": SW_A_SHARE_ID, "name": "申万A指", "level": "L1"}
    )
    ids = [row["id"] for row in svc.load_quote_list()]
    assert ids.count(SW_A_SHARE_ID) == 1


def test_stock_industry_includes_level_names():
    svc, _ = _service()
    rows = svc.load_stock_industry("000001.SZ")
    assert rows[0]["l1_name"] == "农林牧渔"
    assert rows[0]["l2_name"] == "种植业"
    assert rows[0]["l3_name"] == ""


def test_kline_batch_filters_by_id_and_date():
    svc, tables = _service()
    grouped = svc.load_kline_batch(["801010.SI"], start_date="20240101", end_date="20240131")
    condition, params, order_by = tables["sys_data_sw_industry_kline"].calls[-1]
    assert "id IN (%s)" in condition
    assert "date >= %s" in condition
    assert params == ("801010.SI", "20240101", "20240131")
    assert order_by == "id ASC, date ASC"
    assert grouped["801010.SI"][0]["close"] == 1.0
