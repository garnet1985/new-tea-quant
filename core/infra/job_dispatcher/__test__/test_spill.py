from __future__ import annotations

from pathlib import Path

from core.infra.job_dispatcher.spill import (
    cleanup_data_refs,
    load_slot_rows,
    spill_slot_rows,
)
from core.infra.job_dispatcher.types import DataRef


def test_spill_and_load_roundtrip(tmp_path: Path):
    slot_data = {
        "stock.kline": [{"date": "20250101", "close": 1.0}],
        "macro.gdp": [{"date": "20250101", "value": 2.0}],
    }
    refs = spill_slot_rows(tmp_path, "job-1", slot_data)
    assert len(refs) == 2
    loaded = load_slot_rows(refs)
    assert loaded == slot_data
    cleanup_data_refs(refs)
    assert not (tmp_path / "job-1").exists()
