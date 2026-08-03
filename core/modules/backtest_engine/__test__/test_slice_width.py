"""Unit tests for formal slice width resolution."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
    SliceWidthError,
    resolve_reader_queue_depth,
    resolve_slice_open_days,
)


def test_single_slice_start_uses_need_not_full_cap() -> None:
    # Huge memory → cap >> min_required; prefer start ASAP at max(floor, min_required).
    width = resolve_slice_open_days(
        available_mb=100_000.0,
        in_flight=2,
        mb_per_open_day=1.0,
        min_required=100,
        total_open_days=800,
        floor=20,
        ux_hard_max=500,
    )
    assert width == 100


def test_floor_when_min_required_below_floor() -> None:
    width = resolve_slice_open_days(
        available_mb=100_000.0,
        in_flight=2,
        mb_per_open_day=1.0,
        min_required=5,
        total_open_days=800,
        floor=20,
        ux_hard_max=500,
    )
    assert width == 20


def test_fail_when_cap_below_floor() -> None:
    with pytest.raises(SliceWidthError, match="最小片宽"):
        resolve_slice_open_days(
            available_mb=30.0,
            in_flight=2,
            mb_per_open_day=1.0,
            min_required=5,
            total_open_days=800,
            floor=20,
            ux_hard_max=500,
            discount=0.8,
        )


def test_fail_when_in_flight_cannot_cover_min_required() -> None:
    # mem_cap ≈ floor(1000/2/1*0.8)=400, but raise min_required beyond 2*cap
    with pytest.raises(SliceWidthError, match="盖不住 min_required"):
        resolve_slice_open_days(
            available_mb=100.0,
            in_flight=2,
            mb_per_open_day=1.0,
            min_required=500,
            total_open_days=800,
            floor=20,
            ux_hard_max=500,
            discount=0.8,
        )


def test_width_with_large_in_flight_still_prefers_min_required() -> None:
    width = resolve_slice_open_days(
        available_mb=10_000.0,
        in_flight=9,
        mb_per_open_day=1.0,
        min_required=100,
        total_open_days=800,
        floor=20,
        ux_hard_max=500,
    )
    assert width == 100


def test_delayed_start_when_cap_between_floor_and_min_required() -> None:
    # cap = floor(400/2/1*0.8)=160; min_required=200; 2*160>=200 → width=cap=160
    width = resolve_slice_open_days(
        available_mb=400.0,
        in_flight=2,
        mb_per_open_day=1.0,
        min_required=200,
        total_open_days=800,
        floor=20,
        ux_hard_max=500,
        discount=0.8,
    )
    assert width == 160


def test_reader_queue_scales_down_under_pressure() -> None:
    depth = resolve_reader_queue_depth(
        available_mb=100.0,
        mb_per_slice=40.0,
        compute_processes=1,
        current_depth=4,
        high_watermark=0.85,
        low_watermark=0.60,
    )
    assert depth < 4
    assert depth >= 1


def test_reader_queue_may_scale_up_when_slack() -> None:
    depth = resolve_reader_queue_depth(
        available_mb=10_000.0,
        mb_per_slice=10.0,
        compute_processes=1,
        current_depth=1,
        high_watermark=0.85,
        low_watermark=0.60,
    )
    assert depth >= 1
