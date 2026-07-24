"""price_factor.resolve_simulation_window：枚举 period → start/end。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.strategy.core.engines.shared.services.simulation_input.artifact_paths import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.engines.shared.services.simulation_input.enum_loader import load_enum_version
from core.modules.strategy.core.engines.price_factor.timeline import resolve_simulation_window

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


def test_resolve_simulation_window_uses_runtime_period(tmp_path: Path) -> None:
    _write_runtime(tmp_path, start="20240102", end="20240105")
    data = load_enum_version(tmp_path, "1")
    start, end = resolve_simulation_window(data)
    assert start == "20240102"
    assert end == "20240105"


def test_resolve_simulation_window_requires_period(tmp_path: Path) -> None:
    _write_runtime(tmp_path, start="", end="")
    data = load_enum_version(tmp_path, "1")
    with pytest.raises(ValueError, match="period"):
        resolve_simulation_window(data)
