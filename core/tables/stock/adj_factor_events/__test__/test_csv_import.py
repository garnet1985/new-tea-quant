"""adj_factor_events CSV 契约导入。"""
from typing import Optional

import pytest

from core.tables.stock.adj_factor_events.csv_import import (
    CsvImportRejected,
    prepare_adj_factor_csv_import,
)


def _row(sid: str, ed: str, *, lu: Optional[str] = "2026-01-01 10:00:00") -> dict:
    return {
        "id": sid,
        "event_date": ed,
        "factor": 1.0,
        "qfq_diff": 0.0,
        "last_update": lu,
    }


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

    def test_partial_as_of_nulls_last_update(self):
        rows, report = prepare_adj_factor_csv_import(
            [_row("000001.SZ", "20230101"), _row("000001.SZ", "20251201")],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids=None,
        )
        assert report.stocks_partial_as_of == ["000001.SZ"]
        assert all(r["last_update"] is None for r in rows)

    def test_rejects_when_start_not_covered(self):
        with pytest.raises(CsvImportRejected) as exc:
            prepare_adj_factor_csv_import(
                [_row("000001.SZ", "20240101")],
                default_start_date="20230101",
                as_of_date="20260101",
                pool_ids={"000001.SZ"},
                list_date_by_id={"000001.SZ": "19910403"},
            )
        assert exc.value.offenders

    def test_list_date_relaxes_start_for_new_listing(self):
        rows, report = prepare_adj_factor_csv_import(
            [_row("688001.SH", "20240701")],
            default_start_date="20230101",
            as_of_date="20260101",
            pool_ids={"688001.SH"},
            list_date_by_id={"688001.SH": "20240701"},
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
