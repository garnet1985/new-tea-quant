"""StrategySettings 指纹 / effective merge 主线。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def _disk() -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "demo"},
        "simulation": {"execution": {"mode": "entity_based"}},
        "data": {"base": {"data_key": "stock.kline.daily"}},
        "scanner": {"adapters": ["console"]},
        "core": {"n": 1},
    }


def test_fingerprint_diff_ignores_scanner_and_meta() -> None:
    disk = _disk()
    user = {
        **disk,
        "scanner": {"adapters": ["webhook"]},
        "meta": {"key": "demo", "display_name": "x"},
        "core": {"n": 2},
    }
    diff = StrategySettings.fingerprint_diff(disk, user)
    assert "scanner" not in diff
    assert "meta" not in diff
    assert diff.get("core") == {"n": 2}


def test_calculate_effective_settings_merges_fingerprint_fields_only() -> None:
    disk = _disk()
    user = {**disk, "core": {"n": 9}, "scanner": {"adapters": ["x"]}}
    effective, settings_diff = StrategySettings.calculate_effective_settings(disk, user)
    assert settings_diff.get("core") == {"n": 9}
    assert effective.core.get("n") == 9
    # scanner 不进指纹 diff → effective 仍为 disk 侧
    assert effective.scanner.adapter_names == ["console"]


def test_fingerprint_hash_stable_under_entity_id_order() -> None:
    settings = StrategySettings.from_dict(_disk())
    a = settings.fingerprint_hash(
        settings_diff={"core": {"n": 1}},
        entity_ids=["000002.SZ", "000001.SZ"],
        start_date="20240101",
        end_date="20240131",
    )
    b = settings.fingerprint_hash(
        settings_diff={"core": {"n": 1}},
        entity_ids=["000001.SZ", "000002.SZ"],
        start_date="20240101",
        end_date="20240131",
    )
    assert a == b
    assert len(a) == 64


def test_fingerprint_hash_changes_when_window_changes() -> None:
    settings = StrategySettings.from_dict(_disk())
    base = dict(
        settings_diff={},
        entity_ids=["000001.SZ"],
        start_date="20240101",
        end_date="20240131",
    )
    h1 = settings.fingerprint_hash(**base)
    h2 = settings.fingerprint_hash(**{**base, "end_date": "20240229"})
    assert h1 != h2
