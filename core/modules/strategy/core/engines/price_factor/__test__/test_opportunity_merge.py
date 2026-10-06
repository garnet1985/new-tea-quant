"""opportunity_axis_gap / is_new_by_merge_gap。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.price_factor.helpers.opportunity_merge import (
    axis_from_klines,
    is_new_by_merge_gap,
    opportunity_axis_gap,
)

pytestmark = pytest.mark.force_run


def test_axis_gap_adjacent_is_one() -> None:
    axis = ["20240201", "20240202", "20240203", "20240205"]
    assert opportunity_axis_gap("20240201", "20240202", axis) == 1
    assert opportunity_axis_gap("20240201", "20240205", axis) == 3
    assert opportunity_axis_gap("20240201", "20240201", axis) == 0


def test_axis_from_klines_keeps_order() -> None:
    rows = [{"date": "20240201"}, {"date": "20240201"}, {"date": "20240203"}]
    assert axis_from_klines(rows) == ["20240201", "20240203"]


def test_is_new_by_merge_gap_default() -> None:
    assert is_new_by_merge_gap(previous_exists=False, gap=None) is True
    assert is_new_by_merge_gap(previous_exists=True, gap=1, merge_gap=1) is False
    assert is_new_by_merge_gap(previous_exists=True, gap=2, merge_gap=1) is True
    assert is_new_by_merge_gap(previous_exists=True, gap=1, merge_gap=0) is True
    assert is_new_by_merge_gap(previous_exists=True, gap=None, merge_gap=1) is True
