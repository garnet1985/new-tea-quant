"""price_factor.resolve_timeline：枚举 period → 开市日日历轴。"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_consts import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.engines.price_factor.enum_data import load_enum_version
from core.modules.strategy.core.engines.price_factor.timeline import resolve_price_timeline

pytestmark = pytest.mark.force_run


def _write_runtime(output_dir: Path, *, start: str, end: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ENTITY_IDS_FILE).write_text("000001.SZ\n", encoding="utf-8")
    payload = {
        "strategy_key": "demo",
        "version_id": 1,
        "execution_mode": "entity_based",
        "market_profile": "china_a_stock",
        "period": {"start_date": start, "end_date": end},
        "fingerprints": {"settings": "s", "env": "e"},
        "system": {},
        "settings": {"effective_settings": {"market_profile": "china_a_stock"}},
    }
    (output_dir / RUNTIME_ENV_FILE).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_resolve_price_timeline_uses_runtime_period(tmp_path: Path) -> None:
    _write_runtime(tmp_path, start="20240102", end="20240105")
    data = load_enum_version(tmp_path, "1")
    open_dates = ["20240102", "20240103", "20240104", "20240105"]

    with patch(
        "core.modules.strategy.core.engines.price_factor.timeline.BacktestCalendarResolver.resolve",
        return_value=(open_dates, {"open_dates": open_dates}),
    ) as resolve_mock:
        timeline = resolve_price_timeline(data)

    resolve_mock.assert_called_once()
    kwargs = resolve_mock.call_args.kwargs
    assert kwargs["start_date"] == "20240102"
    assert kwargs["end_date"] == "20240105"
    assert timeline.kind == "calendar"
    assert list(timeline.points) == open_dates
    assert timeline.start == "20240102"
    assert timeline.end == "20240105"


def test_resolve_price_timeline_requires_period(tmp_path: Path) -> None:
    _write_runtime(tmp_path, start="", end="")
    data = load_enum_version(tmp_path, "1")
    with pytest.raises(ValueError, match="period"):
        resolve_price_timeline(data)
