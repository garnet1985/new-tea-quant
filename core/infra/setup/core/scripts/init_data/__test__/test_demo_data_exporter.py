"""演示导出：ST 时段按与日期窗相交，不按 start_date BETWEEN。"""

from core.infra.setup.core.scripts.init_data.config import EXPORT_TABLES
from core.infra.setup.core.scripts.init_data.demo_data_exporter import (
    build_date_condition,
    build_table_export_condition,
)


def test_st_periods_export_spec_is_overlap():
    spec = EXPORT_TABLES["sys_stock_st_periods"]
    assert spec.date_filter == ("start_date", "yyyymmdd_overlap")
    assert spec.stock_column == "stock_id"


def test_yyyymmdd_overlap_binds_window_end_then_start():
    sql, params = build_date_condition(
        ("start_date", "yyyymmdd_overlap"),
        full=False,
        start_date="20250101",
        end_date="20260101",
        start_quarter="2025Q1",
        end_quarter="2025Q4",
    )
    assert "start_date <= %s" in sql
    assert "end_date >= %s" in sql
    assert params == ("20260101", "20250101")


def test_st_table_export_condition_keeps_overlap_and_pool():
    spec = EXPORT_TABLES["sys_stock_st_periods"]
    sql, params = build_table_export_condition(
        spec,
        stock_ids=["600070.SH", "000001.SZ"],
        full=False,
        start_date="20250101",
        end_date="20260101",
        start_quarter="2025Q1",
        end_quarter="2025Q4",
    )
    assert "start_date <= %s" in sql
    assert "stock_id IN" in sql
    assert params[:2] == ("20260101", "20250101")
    assert params[2:] == ("600070.SH", "000001.SZ")


def test_point_series_still_uses_between():
    sql, params = build_date_condition(
        ("date", "yyyymmdd"),
        full=False,
        start_date="20250101",
        end_date="20260101",
        start_quarter="2025Q1",
        end_quarter="2025Q4",
    )
    assert sql == "date >= %s AND date <= %s"
    assert params == ("20250101", "20260101")
