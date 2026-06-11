"""adj_factor_events CSV 契约导入。"""
from typing import Optional

import pytest

import pandas as pd

from core.tables.stock.adj_factor_events.csv_import import (
    CsvImportRejected,
    prepare_adj_factor_csv_import,
    validate_csv_columns,
)


def _row(sid: str, ed: str, *, lu: Optional[str] = "2026-01-01 10:00:00") -> dict:
    return {
        "id": sid,
        "event_date": ed,
        "factor": 1.0,
        "qfq_diff": 0.0,
        "last_update": lu,
    }


class TestValidateCsvColumns:
    def test_accepts_pandas_index(self):
        cols = pd.Index(["id", "event_date", "factor", "qfq_diff", "qfq_anchor"])
        validate_csv_columns(cols)

    def test_rejects_missing_columns(self):
        with pytest.raises(CsvImportRejected):
            validate_csv_columns(pd.Index(["id", "event_date"]))


class TestPrepareAdjFactorCsvImport:
    def test_full_cover_truncates_and_keeps_last_update(self):
        rows, report = prepare_adj_factor_csv_import(
            [
                _row("000001.SZ", "20221230"),
                _row("000001.SZ", "20251231"),
                _row("000001.SZ", "20260101"),
                _row("000001.SZ", "20260201"),
                _row("000002.SZ", "20230101"),
                _row("000002.SZ", "20260101", lu="2026-06-09 12:00:00"),
            ],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"000001.SZ", "000002.SZ"},
            list_date_by_id={"000001.SZ": "19910403", "000002.SZ": "19910129"},
        )
        assert report.rows_imported == 5
        assert report.stocks_imported == 2
        assert set(report.stocks_as_of_covered) == {"000001.SZ", "000002.SZ"}
        assert report.stocks_partial_as_of == []
        assert all(r["last_update"] for r in rows)
        dates = {r["event_date"] for r in rows if r["id"] == "000001.SZ"}
        assert dates == {"20221230", "20251231", "20260101"}
        lu_by_ed = {r["event_date"]: r["last_update"] for r in rows if r["id"] == "000002.SZ"}
        assert lu_by_ed["20260101"] == "2026-01-01 23:59:59"
        assert lu_by_ed["20230101"] == "2026-01-01 10:00:00"

    def test_partial_pool_imports_present_stocks(self):
        rows, report = prepare_adj_factor_csv_import(
            [_row("000001.SZ", "20230101")],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"000001.SZ", "000002.SZ"},
        )
        assert len(rows) == 1
        assert report.pool_missing_stocks == ["000002.SZ"]

    def test_drops_outside_pool(self):
        rows, report = prepare_adj_factor_csv_import(
            [
                _row("000001.SZ", "20230101"),
                _row("999999.SZ", "20230101"),
            ],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"000001.SZ"},
        )
        assert len(rows) == 1
        assert report.stocks_dropped_outside_pool == 1

    def test_import_stamps_last_update_even_when_max_event_before_as_of(self):
        """除权日稀疏：末笔事件早于 as_of 仍戳 last_update，供 L0 跳过。"""
        rows, report = prepare_adj_factor_csv_import(
            [_row("000001.SZ", "20230101"), _row("000001.SZ", "20251201")],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids=None,
        )
        assert report.stocks_as_of_covered == ["000001.SZ"]
        assert all(r["last_update"] for r in rows)
        assert all("2026-01-01" in r["last_update"] for r in rows)

    def test_skips_stock_when_start_not_covered(self):
        rows, report = prepare_adj_factor_csv_import(
            [_row("000001.SZ", "20240101")],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"000001.SZ"},
            list_date_by_id={"000001.SZ": "19910403"},
        )
        assert rows == []
        assert report.stocks_skipped_start_coverage == ["000001.SZ"]

    def test_skips_bad_stocks_imports_good_ones(self):
        rows, report = prepare_adj_factor_csv_import(
            [
                _row("000001.SZ", "20240101"),
                _row("000002.SZ", "20230101"),
                _row("000002.SZ", "20260101"),
            ],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"000001.SZ", "000002.SZ"},
            list_date_by_id={"000001.SZ": "19910403", "000002.SZ": "19910129"},
        )
        assert report.stocks_skipped_start_coverage == ["000001.SZ"]
        assert report.stocks_imported == 1
        assert {r["id"] for r in rows} == {"000002.SZ"}

    def test_list_date_relaxes_start_for_new_listing(self):
        rows, report = prepare_adj_factor_csv_import(
            [_row("688001.SH", "20240701")],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"688001.SH"},
            list_date_by_id={"688001.SH": "20240701"},
        )
        assert report.rows_imported == 1

    def test_bj_new_listing_first_event_after_list_date_ok(self):
        """北交所新股：首笔除权晚于上市日，不应触发整批拒绝。"""
        rows, report = prepare_adj_factor_csv_import(
            [_row("920026.BJ", "20240705")],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"920026.BJ"},
            list_date_by_id={"920026.BJ": "20231019"},
        )
        assert report.rows_imported == 1

    def test_no_pool_imports_all_stocks(self):
        rows, report = prepare_adj_factor_csv_import(
            [_row("000001.SZ", "20230101"), _row("000002.SZ", "20230101")],
            default_start_date="20230101",
            as_of_date=None,
            pool_ids=None,
        )
        assert report.stocks_imported == 2
        assert all(r["last_update"] is None for r in rows)
