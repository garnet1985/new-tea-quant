"""stock_list 样本截取。"""
import os

from core.modules.data_source.service import sample_stock_list as mod
from core.modules.data_source.service.sample_stock_list import (
    slice_stock_list,
    slice_stock_list_in_dependencies,
)


def test_slice_stock_list_no_env():
    mod._LOGGED = False
    rows = [{"id": f"{i:06d}"} for i in range(10)]
    assert slice_stock_list(rows) == rows


def test_slice_stock_list_with_limit_and_offset(monkeypatch):
    mod._LOGGED = False
    monkeypatch.setenv("NTQ_DS_SAMPLE_N", "3")
    monkeypatch.setenv("NTQ_DS_SAMPLE_OFFSET", "2")
    rows = [{"id": f"{i:06d}"} for i in range(10)]
    out = slice_stock_list(rows)
    assert len(out) == 3
    assert out[0]["id"] == "000002"


def test_slice_in_dependencies(monkeypatch):
    mod._LOGGED = False
    monkeypatch.setenv("NTQ_DS_SAMPLE_SIZE", "2")
    deps = {"stock_list": [{"id": "a"}, {"id": "b"}, {"id": "c"}], "other": 1}
    out = slice_stock_list_in_dependencies(deps)
    assert len(out["stock_list"]) == 2
    assert out["other"] == 1
    assert deps["stock_list"]  # 原 dict 未改
