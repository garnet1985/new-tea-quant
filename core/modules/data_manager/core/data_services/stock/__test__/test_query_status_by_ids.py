"""StockService.query_status_by_ids — ST 区间 + 退市日合并。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.force_run

from core.modules.data_manager.core.data_services.stock.stock_service import (
    StockService,
)


def _service(*, periods_by_id, list_rows):
    svc = StockService.__new__(StockService)
    svc.st = SimpleNamespace(
        load_overlapping=lambda ids, period_start, period_end: {
            sid: list(periods_by_id.get(sid) or []) for sid in ids
        }
    )
    svc._stock_list = SimpleNamespace(load_by_ids=lambda ids: list(list_rows))
    return svc


def test_query_status_merges_st_and_delisted():
    svc = _service(
        periods_by_id={
            "600000.SH": [
                {
                    "stock_id": "600000.SH",
                    "st_level": "ST",
                    "start_date": "20240101",
                    "end_date": "20241231",
                }
            ],
            "002505.SZ": [],
        },
        list_rows=[
            {"id": "600000.SH", "delist_date": "0"},
            {"id": "002505.SZ", "delist_date": "20240830"},
        ],
    )
    out = svc.query_status_by_ids(
        ["600000.SH", "002505.SZ", "600000.SH"],
        "2024-09-01",
    )
    assert out["600000.SH"] == ["st"]
    assert out["002505.SZ"] == ["delisted"]
    assert list(out.keys()) == ["600000.SH", "002505.SZ"]


def test_query_status_star_st_and_empty_date():
    svc = _service(
        periods_by_id={
            "300108.SZ": [
                {
                    "stock_id": "300108.SZ",
                    "st_level": "STAR_ST",
                    "start_date": "20240101",
                    "end_date": None,
                }
            ]
        },
        list_rows=[{"id": "300108.SZ", "delist_date": ""}],
    )
    assert svc.query_status_by_ids(["300108.SZ"], "20240201") == {
        "300108.SZ": ["star_st"]
    }
    assert svc.query_status_by_ids(["300108.SZ"], "") == {"300108.SZ": []}
