"""ListService 全局样本池过滤。"""
from unittest.mock import MagicMock

from core.modules.data_manager.data_services.stock.sub_services.list_service import (
    ListService,
)
from core.modules.data_source.service import sample_stock_list as mod


def test_load_all_applies_sample_pool(monkeypatch, tmp_path):
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n000002.SZ\n", encoding="utf-8")
    mod.invalidate_pool_cache()
    monkeypatch.setattr(mod, "sample_pool_count", lambda: 500)
    monkeypatch.setattr(mod, "pool_csv_path", lambda _count: pool)

    dm = MagicMock()
    stock_list_model = MagicMock()
    stock_list_model.load_all_stocks.return_value = [
        {"id": "000001.SZ"},
        {"id": "000002.SZ"},
        {"id": "000003.SZ"},
    ]
    dm.get_table.return_value = stock_list_model

    svc = ListService(dm)
    out = svc.load_all()
    assert [r["id"] for r in out] == ["000001.SZ", "000002.SZ"]


def test_load_single_outside_pool_returns_none(monkeypatch):
    mod.invalidate_pool_cache()
    monkeypatch.setattr(
        "core.modules.data_source.service.sample_stock_list._load_pool_ids",
        lambda: ["000001.SZ"],
    )

    dm = MagicMock()
    stock_list_model = MagicMock()
    stock_list_model.load_by_id.return_value = {"id": "000002.SZ"}
    dm.get_table.return_value = stock_list_model

    svc = ListService(dm)
    assert svc.load_single("000002.SZ") is None
