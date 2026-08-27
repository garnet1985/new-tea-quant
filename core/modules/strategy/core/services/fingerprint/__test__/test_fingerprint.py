"""语义 settings 指纹。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

pytestmark = pytest.mark.force_run


def _disk() -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "demo"},
        "simulation": {"execution": {"mode": "entity_based"}},
        "data": {"base": {"data_key": "stock.kline.daily"}},
        "scanner": {"adapters": ["console"]},
        "core": {"n": 1},
        "analysis": {"enabled": True},
    }


def test_semantic_fingerprint_ignores_analysis_only_change() -> None:
    disk = _disk()
    effective_a, _ = StrategySettings.calculate_effective_settings(disk, {})
    user = {**disk, "analysis": {"enabled": False, "extra": 1}}
    effective_b, _ = StrategySettings.calculate_effective_settings(disk, user)
    ids = ["000001.SZ"]
    fp_a = FingerprintCalculator.to_effective_settings_fingerprint(effective_a, ids)
    fp_b = FingerprintCalculator.to_effective_settings_fingerprint(effective_b, ids)
    assert fp_a == fp_b


def test_calculate_fingerprints_result_has_no_entity_cache() -> None:
    """指纹结果不含运行时 cache；entity_ids 由调用方传入。"""
    from types import SimpleNamespace

    info = SimpleNamespace(
        settings={"simulation": {"execution": {"mode": "entity_based"}}},
        unique_relative_path="demo/x",
        hooks_class=None,
        hooks_module_path="",
        strategy_file="",
    )
    result = FingerprintCalculator.calculate_fingerprints(
        info, {}, entity_ids=["000001.SZ"]
    )
    assert result.entity_ids == ["000001.SZ"]
    assert result.settings_fp
    assert result.env_fp
    assert not hasattr(result, "global_entity_cache")


def test_semantic_fingerprint_stable_after_round_trip() -> None:
    disk = _disk()
    effective, _ = StrategySettings.calculate_effective_settings(disk, {"core": {"n": 2}})
    ids = ["000001.SZ"]
    subset = StrategySettings.extract_effective_settings(effective)
    fp1 = FingerprintCalculator.to_effective_settings_fingerprint(effective, ids)
    reloaded = StrategySettings.from_dict(
        {**disk, **StrategySettings.merge_disk_with_diff(disk, {"core": {"n": 2}})}
    )
    fp2 = FingerprintCalculator.to_effective_settings_fingerprint(reloaded, ids)
    assert StrategySettings.extract_effective_settings(reloaded) == subset
    assert fp1 == fp2
