"""stock_list 样本宇宙（data.json use_sample_stock_list → DataManager.sample_universe）。"""
from pathlib import Path

from core.modules.data_manager import DataManager


def test_slice_stock_list_no_config(monkeypatch):
    DataManager.sample_universe.invalidate_cache()
    monkeypatch.setattr(DataManager.sample_universe, "count", lambda: None)
    rows = [{"id": f"{i:06d}"} for i in range(10)]
    assert DataManager.sample_universe.slice_stock_list(rows) == rows


def test_slice_stock_list_by_dev_pool(monkeypatch, tmp_path: Path):
    DataManager.sample_universe.invalidate_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id,list_status\n000002.SZ,L\n000001.SZ,L\n", encoding="utf-8")
    monkeypatch.setattr(DataManager.sample_universe, "count", lambda: 500)
    monkeypatch.setattr(DataManager.sample_universe, "csv_path", lambda _count: pool)

    rows = [{"id": "000001.SZ"}, {"id": "000002.SZ"}, {"id": "000003.SZ"}]
    out = DataManager.sample_universe.slice_stock_list(rows)
    assert [r["id"] for r in out] == ["000002.SZ", "000001.SZ"]


def test_csv_path_rejects_invalid_count():
    try:
        DataManager.sample_universe.csv_path(0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_csv_path_uses_dev_directory():
    p = DataManager.sample_universe.csv_path(DataManager.sample_universe.DEFAULT_COUNT)
    assert p.name == "stratified_500.csv"
    assert p.parent.name == "sample_stock_list"
    assert p.parent.parent.name == "dev"


def test_slice_in_dependencies(monkeypatch, tmp_path: Path):
    DataManager.sample_universe.invalidate_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n000002.SZ\n", encoding="utf-8")
    monkeypatch.setattr(DataManager.sample_universe, "count", lambda: 500)
    monkeypatch.setattr(DataManager.sample_universe, "csv_path", lambda _count: pool)
    deps = {
        "stock_list": [{"id": "000001.SZ"}, {"id": "000002.SZ"}, {"id": "000003.SZ"}],
        "other": 1,
    }
    out = DataManager.sample_universe.slice_stock_list_in_dependencies(deps)
    assert len(out["stock_list"]) == 2
    assert out["other"] == 1
    assert deps["stock_list"]


def test_filter_paired(monkeypatch, tmp_path: Path):
    DataManager.sample_universe.invalidate_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n", encoding="utf-8")
    monkeypatch.setattr(DataManager.sample_universe, "count", lambda: 500)
    monkeypatch.setattr(DataManager.sample_universe, "csv_path", lambda _count: pool)
    main = [{"id": "000001.SZ"}, {"id": "000002.SZ"}]
    raw = [{"industry": "A"}, {"industry": "B"}]
    m, r = DataManager.sample_universe.filter_paired(main, raw)
    assert len(m) == 1
    assert m[0]["id"] == "000001.SZ"
    assert r[0]["industry"] == "A"


def test_is_active(monkeypatch, tmp_path: Path):
    DataManager.sample_universe.invalidate_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n", encoding="utf-8")
    monkeypatch.setattr(DataManager.sample_universe, "count", lambda: 500)
    monkeypatch.setattr(DataManager.sample_universe, "csv_path", lambda _count: pool)
    assert DataManager.sample_universe.is_active() is True


def test_stock_id_field_for_schema():
    su = DataManager.sample_universe
    assert su.stock_id_field_for_schema({"primaryKey": ["id", "date"]}) == "id"
    assert su.stock_id_field_for_schema({"primaryKey": ["stock_id", "date"]}) == "stock_id"
    assert su.stock_id_field_for_schema({"primaryKey": ["date"]}) is None


def test_filter_records(monkeypatch, tmp_path: Path):
    DataManager.sample_universe.invalidate_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n000002.SZ\n", encoding="utf-8")
    monkeypatch.setattr(DataManager.sample_universe, "count", lambda: 500)
    monkeypatch.setattr(DataManager.sample_universe, "csv_path", lambda _count: pool)
    schema = {"primaryKey": ["id", "date"]}
    rows = [
        {"id": "000001.SZ", "date": "20240101"},
        {"id": "000003.SZ", "date": "20240101"},
        {"id": "000002.SZ", "date": "20240101"},
    ]
    out = DataManager.sample_universe.filter_records(rows, schema)
    assert [r["id"] for r in out] == ["000001.SZ", "000002.SZ"]


def test_filter_records_skips_non_stock_schema(monkeypatch, tmp_path: Path):
    DataManager.sample_universe.invalidate_cache()
    pool = tmp_path / "stratified_500.csv"
    pool.write_text("id\n000001.SZ\n", encoding="utf-8")
    monkeypatch.setattr(DataManager.sample_universe, "count", lambda: 500)
    monkeypatch.setattr(DataManager.sample_universe, "csv_path", lambda _count: pool)
    rows = [{"date": "20240101", "value": 1.0}]
    assert DataManager.sample_universe.filter_records(rows, {"primaryKey": ["date"]}) == rows
