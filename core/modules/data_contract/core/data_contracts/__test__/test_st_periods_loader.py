"""ST loader：与窗相交的时段留下，窗口前已生效的收到窗首日。"""

from core.modules.data_contract.core.data_contracts.stock_st_periods.loader import (
    StockStPeriodsLoader,
)


def test_clip_carries_open_period_started_before_window():
    rows = [
        {
            "stock_id": "600070.SH",
            "st_level": "STAR_ST",
            "start_date": "20240430",
            "end_date": None,
        },
        {
            "stock_id": "600070.SH",
            "st_level": "ST",
            "start_date": "20200101",
            "end_date": "20241231",
        },
    ]
    out = StockStPeriodsLoader._clip_to_window(
        rows, {"start": "20250101", "end": "20260101"}
    )
    assert len(out) == 1
    assert out[0]["st_level"] == "STAR_ST"
    assert out[0]["start_date"] == "20250101"
    assert out[0]["end_date"] is None


def test_clip_keeps_in_window_period_unchanged():
    rows = [
        {
            "stock_id": "000488.SZ",
            "st_level": "ST",
            "start_date": "20250221",
            "end_date": None,
        }
    ]
    out = StockStPeriodsLoader._clip_to_window(
        rows, {"start": "20250101", "end": "20260101"}
    )
    assert out[0]["start_date"] == "20250221"


def test_clip_without_window_is_passthrough():
    rows = [{"start_date": "20240430", "end_date": None}]
    assert StockStPeriodsLoader._clip_to_window(rows, {}) == rows
