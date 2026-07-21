"""SimulationCacheManager 双指纹槽位读写（mock 表）。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.modules.strategy.contracts import SimulateKind
from core.modules.strategy.core.services.simulation_cache.cache_manager import (
    SimulationCacheManager,
)


def _fps(**overrides):
    base = {
        "settings_fp": "sfp",
        "env_fp": "efp",
        "disk_settings_hash": "dsh",
        "settings_diff": {"sampling": {"use_sampling": True}},
        "effective_settings": None,
        "entity_ids": [],
        "global_entity_cache": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_get_cache_hit_returns_kind_shaped_payload():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {
            "version": 2,
            "result_report": {
                "enum": {"version_id": "v1", "success": True},
            },
        }
    ]
    with patch.object(SimulationCacheManager, "_table", return_value=model):
        hit = SimulationCacheManager.get_cache(
            "demo/strategy",
            _fps(),
            SimulateKind.ENUMERATE,
        )
    assert hit == {
        SimulateKind.ENUMERATE.value: {"version_id": "v1", "success": True}
    }


def test_get_cache_miss_when_slot_empty():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {"version": 2, "result_report": {"price_factor": {"ok": 1}}}
    ]
    with patch.object(SimulationCacheManager, "_table", return_value=model):
        hit = SimulationCacheManager.get_cache(
            "demo/strategy",
            _fps(),
            SimulateKind.ENUMERATE,
        )
    assert hit is None


def test_set_cache_enum_clears_downstream_on_update():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {
            "version": 3,
            "result_report": {
                "enum": {"version_id": "old"},
                "price_factor": {"win_rate": 50.0},
                "capital_allocation": {"total_return": 0.1},
            },
        }
    ]
    with patch.object(SimulationCacheManager, "_table", return_value=model):
        version = SimulationCacheManager.set_cache(
            "demo/strategy",
            _fps(),
            {SimulateKind.ENUMERATE.value: {"version_id": "new", "success": True}},
        )
    assert version == 3
    merged = model.update_result_report.call_args[0][2]
    assert merged["enum"]["version_id"] == "new"
    assert "price_factor" not in merged
    assert "capital_allocation" not in merged


def test_set_cache_creates_row_when_miss():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = []
    model.create_snapshot.return_value = {"strategy_name": "demo/strategy", "version": 1}
    with patch.object(SimulationCacheManager, "_table", return_value=model):
        version = SimulationCacheManager.set_cache(
            "demo/strategy",
            _fps(),
            {"enumerate": {"version_id": "v9", "success": True}},
        )
    assert version == 1
    created_report = model.create_snapshot.call_args[0][2]
    assert created_report["enum"]["version_id"] == "v9"


def test_find_enum_output_version():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {"version": 1, "result_report": {"enum": {"version_id": "out-12"}}}
    ]
    with patch.object(SimulationCacheManager, "_table", return_value=model):
        assert (
            SimulationCacheManager.find_enum_output_version("demo/strategy", _fps())
            == "out-12"
        )


def test_get_cache_price_factor_slot():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {
            "version": 4,
            "result_report": {
                "enum": {"version_id": "v1"},
                "price_factor": {"version_id": 2, "success": True},
            },
        }
    ]
    with patch.object(SimulationCacheManager, "_table", return_value=model):
        hit = SimulationCacheManager.get_cache(
            "demo/strategy",
            _fps(),
            SimulateKind.PRICE_FACTOR,
        )
    assert hit == {
        SimulateKind.PRICE_FACTOR.value: {"version_id": 2, "success": True}
    }


def test_set_cache_price_factor_merges_without_clearing_enum():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {
            "version": 5,
            "result_report": {"enum": {"version_id": "v1"}},
        }
    ]
    with patch.object(SimulationCacheManager, "_table", return_value=model):
        version = SimulationCacheManager.set_cache(
            "demo/strategy",
            _fps(),
            {
                SimulateKind.PRICE_FACTOR.value: {
                    "version_id": 3,
                    "enum_version_id": "v1",
                    "success": True,
                }
            },
        )
    assert version == 5
    merged = model.update_result_report.call_args[0][2]
    assert merged["enum"]["version_id"] == "v1"
    assert merged["price_factor"]["version_id"] == 3
