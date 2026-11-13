"""演示导出：ST 时段按与日期窗相交，不按 start_date BETWEEN；预设解析。"""

from core.infra.setup.core.scripts.init_data.config import (
    DEFAULT_END_DATE,
    DEFAULT_END_QUARTER,
    DEFAULT_START_DATE,
    DEFAULT_START_QUARTER,
    EXPORT_TABLES,
    TARGET_STOCK_COUNT,
)
from core.infra.setup.core.scripts.init_data.demo_data_exporter import (
    build_date_condition,
    build_table_export_condition,
    normalize_ex_argv,
    resolve_export_plan,
    yyyymmdd_to_quarter,
)


def test_st_periods_export_spec_is_overlap():
    spec = EXPORT_TABLES["sys_data_stock_st_periods"]
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
    spec = EXPORT_TABLES["sys_data_stock_st_periods"]
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


def test_normalize_ex_argv_strips_leading_ddash():
    assert normalize_ex_argv(["--", "--demo"]) == ["--demo"]
    assert normalize_ex_argv(["--member"]) == ["--member"]
    assert normalize_ex_argv(None) == []


def test_yyyymmdd_to_quarter():
    assert yyyymmdd_to_quarter("20230101") == "2023Q1"
    assert yyyymmdd_to_quarter("20261111") == "2026Q4"


def test_resolve_export_plan_demo_defaults():
    plan = resolve_export_plan(
        preset="demo",
        start_date=None,
        end_date=None,
        start_quarter=None,
        end_quarter=None,
        stock_count=None,
        skip_sample=False,
        no_date_filter=False,
    )
    assert plan.preset == "demo"
    assert plan.skip_sample is False
    assert plan.stock_count == TARGET_STOCK_COUNT
    assert plan.no_date_filter is False
    assert plan.start_date == DEFAULT_START_DATE
    assert plan.end_date == DEFAULT_END_DATE
    assert plan.start_quarter == DEFAULT_START_QUARTER
    assert plan.end_quarter == DEFAULT_END_QUARTER


def test_resolve_export_plan_member_full_market_window():
    plan = resolve_export_plan(
        preset="member",
        start_date=None,
        end_date="20261111",
        start_quarter=None,
        end_quarter=None,
        stock_count=None,
        skip_sample=False,
        no_date_filter=False,
    )
    assert plan.skip_sample is True
    assert plan.stock_count == 0
    assert plan.no_date_filter is False
    assert plan.end_date == "20261111"
    assert plan.end_quarter == "2026Q4"


def test_resolve_export_plan_full_implies_no_date_filter():
    plan = resolve_export_plan(
        preset="full",
        start_date=None,
        end_date=None,
        start_quarter=None,
        end_quarter=None,
        stock_count=None,
        skip_sample=False,
        no_date_filter=False,
    )
    assert plan.skip_sample is True
    assert plan.stock_count == 0
    assert plan.no_date_filter is True
