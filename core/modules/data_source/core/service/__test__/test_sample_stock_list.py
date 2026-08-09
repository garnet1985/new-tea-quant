"""stock_list 样本池（data.json use_sample_stock_list → dev/stock_pool）。"""
from pathlib import Path

from core.modules.data_source.core.service import sample_stock_list as mod
from core.modules.data_source.core.service.sample_stock_list import (
    filter_paired_stock_records,
    filter_records_by_sample_pool,
    is_sample_active,
    pool_csv_path,
    slice_stock_list,
    slice_stock_list_in_dependencies,
    stock_id_field_for_schema,
)


def test_slice_stock_list_no_config(monkeypatch):
    mod.invalidate_pool_cache()
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.sample_pool_count",
        lambda: None,
    )
    rows = [{"id": f"{i:06d}"} for i in range(10)]
    assert slice_stock_list(rows) == rows


def test_slice_stock_list_by_dev_pool(monkeypatch, tmp_path: Path):
    mod.invalidate_pool_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id,list_status\n000002.SZ,L\n000001.SZ,L\n", encoding="utf-8")
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.sample_pool_count",
        lambda: 500,
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.pool_csv_path",
        lambda _count: pool,
    )

    rows = [{"id": "000001.SZ"}, {"id": "000002.SZ"}, {"id": "000003.SZ"}]
    out = slice_stock_list(rows)
    assert [r["id"] for r in out] == ["000002.SZ", "000001.SZ"]


def test_pool_csv_path_rejects_invalid_count():
    try:
        pool_csv_path(0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_slice_in_dependencies(monkeypatch, tmp_path: Path):
    mod.invalidate_pool_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n000002.SZ\n", encoding="utf-8")
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.sample_pool_count",
        lambda: 500,
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.pool_csv_path",
        lambda _count: pool,
    )
    deps = {
        "stock_list": [{"id": "000001.SZ"}, {"id": "000002.SZ"}, {"id": "000003.SZ"}],
        "other": 1,
    }
    out = slice_stock_list_in_dependencies(deps)
    assert len(out["stock_list"]) == 2
    assert out["other"] == 1
    assert deps["stock_list"]


def test_filter_paired_stock_records(monkeypatch, tmp_path: Path):
    mod.invalidate_pool_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n", encoding="utf-8")
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.sample_pool_count",
        lambda: 500,
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.pool_csv_path",
        lambda _count: pool,
    )
    main = [{"id": "000001.SZ"}, {"id": "000002.SZ"}]
    raw = [{"industry": "A"}, {"industry": "B"}]
    m, r = filter_paired_stock_records(main, raw)
    assert len(m) == 1
    assert m[0]["id"] == "000001.SZ"
    assert r[0]["industry"] == "A"


def test_is_sample_active(monkeypatch, tmp_path: Path):
    mod.invalidate_pool_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n", encoding="utf-8")
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.sample_pool_count",
        lambda: 500,
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.pool_csv_path",
        lambda _count: pool,
    )
    assert is_sample_active() is True


def test_stock_id_field_for_schema():
    assert stock_id_field_for_schema({"primaryKey": ["id", "date"]}) == "id"
    assert stock_id_field_for_schema({"primaryKey": ["stock_id", "date"]}) == "stock_id"
    assert stock_id_field_for_schema({"primaryKey": ["date"]}) is None


def test_filter_records_by_sample_pool(monkeypatch, tmp_path: Path):
    mod.invalidate_pool_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n000002.SZ\n", encoding="utf-8")
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.sample_pool_count",
        lambda: 500,
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.pool_csv_path",
        lambda _count: pool,
    )
    schema = {"primaryKey": ["id", "date"]}
    rows = [
        {"id": "000001.SZ", "date": "20240101"},
        {"id": "000003.SZ", "date": "20240101"},
        {"id": "000002.SZ", "date": "20240101"},
    ]
    out = filter_records_by_sample_pool(rows, schema)
    assert [r["id"] for r in out] == ["000001.SZ", "000002.SZ"]


def test_filter_records_skips_non_stock_schema(monkeypatch, tmp_path: Path):
    mod.invalidate_pool_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n", encoding="utf-8")
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.sample_pool_count",
        lambda: 500,
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.sample_stock_list.pool_csv_path",
        lambda _count: pool,
    )
    rows = [{"date": "20240101", "value": 1.0}]
    assert filter_records_by_sample_pool(rows, {"primaryKey": ["date"]}) == rows
