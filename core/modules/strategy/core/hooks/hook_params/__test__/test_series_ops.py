"""Series 窗口统计 / 波峰波谷 / 趋势段。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.hooks.hook_params import Series

pytestmark = pytest.mark.force_run


def _closes(*values: float) -> Series:
    return Series(
        [{"date": f"202401{index + 1:02d}", "close": value} for index, value in enumerate(values)]
    )


def _ohlc(rows: list) -> Series:
    return Series(rows)


def test_at_and_window_stats() -> None:
    series = _closes(10, 12, 8, 14)
    assert series.at("close") == 14
    assert series.at("close", 0) == 10
    assert series.min_of("close", 3) == 8
    assert series.max_of("close", 3) == 14
    assert series.mean_of("close", 2) == 11
    assert series.min_of("close", 0) is None
    assert series.at("missing") is None


def test_pct_change_rising_falling_streak() -> None:
    series = _closes(10, 11, 12, 11, 10, 9)
    assert series.pct_change() == pytest.approx(-0.1)
    assert series.pct_change(n=2) == pytest.approx((9 - 11) / 11)
    assert _closes(1, 2, 3).rising(n=2) is True
    assert _closes(3, 2, 1).falling(n=2) is True
    assert _closes(1, 2, 2).rising() is False
    assert series.streak() == -3
    assert _closes(1, 2, 3, 4).streak() == 3
    assert _closes(1, 1).streak() == 0


def test_crossed_above_and_below() -> None:
    series = Series(
        [
            {"date": "20240101", "close": 9, "sma": 10},
            {"date": "20240102", "close": 11, "sma": 10},
        ]
    )
    assert series.crossed_above("close", "sma") is True
    assert series.crossed_below("close", "sma") is False
    assert series.crossed_above("close", 10) is True

    down = Series(
        [
            {"date": "20240101", "close": 11, "sma": 10},
            {"date": "20240102", "close": 9, "sma": 10},
        ]
    )
    assert down.crossed_below("close", "sma") is True
    assert down.crossed_above("close", 10) is False


def test_find_peaks_and_valleys() -> None:
    # order=1: peaks at 5 and local 2; valley at 1
    series = _closes(1, 3, 5, 4, 1, 2, 0)
    peaks = series.find_peaks(field="close", order=1)
    valleys = series.find_valleys(field="close", order=1)
    assert [item["index"] for item in peaks] == [2, 5]
    assert peaks[0]["kind"] == "peak"
    assert peaks[0]["value"] == 5
    assert [item["index"] for item in valleys] == [4]
    assert valleys[0]["kind"] == "valley"
    assert valleys[0]["value"] == 1

    # plateau is not a strict extremum
    flat = _closes(1, 3, 3, 2)
    assert flat.find_peaks(field="close", order=1) == []


def test_swing_points_and_to_trend() -> None:
    rows = [
        {"date": "d0", "high": 3, "low": 1, "close": 2},
        {"date": "d1", "high": 5, "low": 2, "close": 4},  # peak high
        {"date": "d2", "high": 4, "low": 0.5, "close": 1},  # valley low
        {"date": "d3", "high": 6, "low": 2, "close": 5},  # peak high
        {"date": "d4", "high": 5, "low": 3, "close": 4},
    ]
    series = _ohlc(rows)
    swings = series.swing_points(order=1)
    assert [(item["index"], item["kind"]) for item in swings] == [
        (1, "peak"),
        (2, "valley"),
        (3, "peak"),
    ]
    segments = series.to_trend(order=1)
    assert len(segments) == 2
    assert segments[0]["direction"] == "down"
    assert segments[0]["start_index"] == 1
    assert segments[0]["end_index"] == 2
    assert segments[1]["direction"] == "up"
    assert segments[1]["start_date"] == "d2"
    assert segments[1]["end_date"] == "d3"


def test_to_trend_empty_without_enough_swings() -> None:
    series = _closes(1, 2, 3)
    assert series.to_trend(field="close", order=2) == []


def test_candle_body_wicks_and_true_range() -> None:
    series = _ohlc(
        [
            {"date": "d0", "open": 10, "high": 12, "low": 9, "close": 11},
            {"date": "d1", "open": 11, "high": 15, "low": 8, "close": 10},
        ]
    )
    assert series.is_bullish(0) is True
    assert series.is_bearish() is True
    assert series.body() == 1
    assert series.upper_wick() == 4  # 15 - max(11, 10)
    assert series.lower_wick() == 2  # min(11, 10) - 8
    # TR = max(15-8, |15-11|, |8-11|) = 7
    assert series.true_range() == 7


def test_breakout_breakdown_and_gap() -> None:
    # 近 3 根高点 13，收 14 突破；含更早 20 时不破
    highs = [20, 11, 12, 13, 14]
    series = Series(
        [
            {"date": f"d{i}", "high": h, "low": 5, "close": h, "open": h}
            for i, h in enumerate(highs)
        ]
    )
    assert series.breakout_above("high", n=3) is True
    assert series.breakout_above("high", n=4) is False

    lows = Series(
        [
            {"date": "d0", "low": 10, "high": 12, "close": 11, "open": 11},
            {"date": "d1", "low": 9, "high": 12, "close": 10, "open": 10},
            {"date": "d2", "low": 8, "high": 12, "close": 9, "open": 9},
            {"date": "d3", "low": 7, "high": 12, "close": 6, "open": 8},
        ]
    )
    assert lows.breakdown_below("low", n=2) is True

    gapped = Series(
        [
            {"date": "d0", "open": 10, "close": 10, "high": 11, "low": 9},
            {"date": "d1", "open": 12, "close": 11, "high": 13, "low": 10},
        ]
    )
    gap = gapped.gap()
    assert gap is not None
    assert gap["kind"] == "up"
    assert gap["pct"] == pytest.approx(0.2)


def test_retracement_from_peak() -> None:
    rows = [
        {"date": "d0", "high": 3, "low": 1, "close": 2},
        {"date": "d1", "high": 5, "low": 2, "close": 4},  # peak
        {"date": "d2", "high": 4, "low": 1, "close": 2},  # valley
        {"date": "d3", "high": 8, "low": 2, "close": 7},  # peak 8
        {"date": "d4", "high": 7, "low": 3, "close": 4},  # current 4
    ]
    series = _ohlc(rows)
    # last peak=8 at d3, prior valley=1 at d2; (8-4)/(8-1) = 4/7
    assert series.retracement(from_peak=True, order=1) == pytest.approx(4 / 7)
