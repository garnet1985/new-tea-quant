"""语义 settings 指纹与磁盘 simulate cache。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.artifacts import RUNTIME_ENV_FILE
from core.modules.strategy.core.services.simulation_cache.fingerprints import (
    FingerprintCalculator,
)
from core.modules.strategy.core.services.simulation_cache.version_store import (
    SimulationVersionStore,
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


def test_disk_cache_hit(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    step_dir = root / "1" / "enum"
    step_dir.mkdir(parents=True)
    (step_dir / RUNTIME_ENV_FILE).write_text(
        json.dumps({"strategy_key": "demo", "settings_fp": "s", "env_fp": "e"}),
        encoding="utf-8",
    )
    (root / "meta.json").write_text(
        json.dumps(
            {
                "registry": {
                    "1": {
                        "settings_fp": "s",
                        "env_fp": "e",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    fps = SimpleNamespace(settings_fp="s", env_fp="e", entity_ids=[], effective_settings=MagicMock())
    from core.modules.strategy.core.services.artifacts import ArtifactStore

    with patch.object(ArtifactStore, "simulations_root", return_value=root), patch.object(
        ArtifactStore,
        "resolve",
        return_value=ArtifactStore.at(step_dir, kind=SimulateKind.ENUMERATE, version_id="1"),
    ), patch.object(
        SimulationVersionStore,
        "_load_ui_dict",
        return_value={"enumMetrics": {"totalOpportunities": 3}},
    ):
        cached = SimulationVersionStore.get_cache(tmp_path, fps, SimulateKind.ENUMERATE)
    assert cached is not None
    assert cached["enumerate"]["version_id"] == "1"
    assert cached["enumerate"]["enumMetrics"]["totalOpportunities"] == 3


def test_disk_cache_miss_when_env_invalid(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    step_dir = root / "1" / "enum"
    step_dir.mkdir(parents=True)
    (step_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    (root / "meta.json").write_text(
        json.dumps(
            {
                "registry": {
                    "1": {
                        "settings_fp": "s",
                        "env_fp": "old-env",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    fps = SimpleNamespace(settings_fp="s", env_fp="new-env", entity_ids=[], effective_settings={})
    from core.modules.strategy.core.services.artifacts import ArtifactStore

    with patch.object(ArtifactStore, "simulations_root", return_value=root):
        cached = SimulationVersionStore.get_cache(tmp_path, fps, SimulateKind.ENUMERATE)
    assert cached is None

