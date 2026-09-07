"""ColumnProfiler — reusable column summary."""
from __future__ import annotations

import pytest

from core.modules.analysis import Analysis

pytestmark = pytest.mark.force_run


def test_summarize_column_constant_numeric() -> None:
    out = Analysis.Classical.summarize_column([1.0, 1.0, 1.0])
    assert out["role"] == "constant"
    assert out["dtype"] == "numeric"
    assert out["value"] == 1.0


def test_summarize_column_varying_numeric() -> None:
    out = Analysis.Classical.summarize_column([1.0, 2.0, 3.0])
    assert out["role"] == "varying"
    assert out["min"] == 1.0
    assert out["max"] == 3.0


def test_coerce_float_rejects_bool() -> None:
    assert Analysis.Classical.coerce_float(True) is None
