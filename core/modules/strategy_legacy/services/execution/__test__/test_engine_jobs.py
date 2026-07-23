"""Strategy → BacktestEngine job wrapping."""
from __future__ import annotations

import pytest

from core.modules.strategy.services.execution.engine_jobs import (
    require_stock_id,
    wrap_timeline_stock_job,
)


def test_wrap_timeline_stock_job() -> None:
    job = {"stock_id": "000001.SZ", "strategy_name": "demo"}
    wrapped = wrap_timeline_stock_job(job, extra_flag=True)
    assert wrapped == {
        "id": "000001.SZ",
        "payload": {"stock_id": "000001.SZ", "strategy_name": "demo", "extra_flag": True},
    }


def test_require_stock_id_raises_without_field() -> None:
    with pytest.raises(ValueError, match="requires stock_id"):
        require_stock_id({}, label="timeline stock job")
