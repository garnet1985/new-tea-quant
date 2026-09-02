"""Simulate 磁盘 version 布局端到端（mock pipeline，真实 registry 写盘）。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import core.modules.strategy.core.strategy as strategy_module
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.consts import (
    EFFECTIVE_SETTINGS_FILE,
    RUNTIME_ENV_FILE,
    SCOPE_FILE,
    SETTINGS_FILE,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.engines.enumerator.pipeline import EnumeratorPipeline
from core.modules.strategy.core.engines.shared.data_class.simulate_session import (
    SimulateSession,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.strategy import Strategy

pytestmark = pytest.mark.force_run


def _prepare_entity_cache(self, **kwargs):
    self.global_entity_cache = MagicMock()
    return self.global_entity_cache


def _fps():
    return SimpleNamespace(
        execute_fp="settings-fp",
        env_fp="env-fp",
        disk_settings_hash="dsh",
        settings_diff={"core": {"n": 1}},
        effective_settings=StrategySettings.from_dict({"core": {"n": 1}}),
        entity_ids=["000001.SZ"],
    )


def test_simulate_miss_writes_disk_registry_and_version_dirs(tmp_path: Path) -> None:
    """``se``/``simulate`` miss 路径：``simulations/{vid}/{step}/`` + meta registry。"""
    strategy_folder = tmp_path / "demo" / "test_strategy"
    strategy_folder.mkdir(parents=True)
    sim_root = strategy_folder / "results" / "simulations"
    output_dir = sim_root / "1" / "enum"
    output_dir.mkdir(parents=True)
    (output_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")

    step_res = {
        "success": True,
        "version_id": "1",
        "output_dir": str(output_dir),
        "opportunities_count": 2,
    }

    info = MagicMock()
    info.id.return_value = "demo/test_strategy"
    info.unique_relative_path = "demo/test_strategy"
    info.key = "test_strategy"
    info.relative_path = "demo/test_strategy"
    info.settings = {"meta": {"key": "test_strategy"}, "core": {"n": 1}}

    with patch.object(
        strategy_module.DiscoveryService,
        "find_strategy",
        return_value=info,
    ), patch.object(
        strategy_module.DiscoveryService,
        "resolve_strategy_folder",
        return_value=strategy_folder,
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_stock_list",
        return_value=["000001.SZ"],
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_latest_completed_trading_date",
        return_value="20240110",
    ), patch.object(
        strategy_module.FingerprintCalculator,
        "calculate_fingerprints",
        return_value=_fps(),
    ), patch.object(
        strategy_module.SimulationVersionStore,
        "get_cache",
        return_value=None,
    ), patch.object(
        SimulateSession,
        "prepare_entity_cache",
        _prepare_entity_cache,
    ), patch.object(
        EnumeratorPipeline,
        "run",
        return_value=step_res,
    ) as run:
        out = Strategy.simulate("demo/test_strategy", kind=SimulateKind.ENUMERATE)

    run.assert_called_once()

    assert out["version_id"] == "1"
    assert out["enumerate"]["version_id"] == "1"

    entry = VersionMetaStore.get_registry_entry(sim_root, "1")
    assert entry is not None
    assert entry["execute_fp"] == "settings-fp"
    assert entry["env_fp"] == "env-fp"

    vid_dir = sim_root / "1"
    settings = json.loads((vid_dir / SETTINGS_FILE).read_text(encoding="utf-8"))
    effective = json.loads((vid_dir / EFFECTIVE_SETTINGS_FILE).read_text(encoding="utf-8"))
    scope = json.loads((vid_dir / SCOPE_FILE).read_text(encoding="utf-8"))
    runtime = json.loads((vid_dir / "enum" / RUNTIME_ENV_FILE).read_text(encoding="utf-8"))
    assert settings["core"]["n"] == 1
    assert "entity_ids" not in effective
    assert "core" in effective
    assert scope["entity_ids"] == ["000001.SZ"]
    assert "execute_fp" not in runtime
    assert "entity_ids" not in runtime
    assert "period" not in runtime
    assert "settings" not in runtime
    assert entry.get("steps", {}).get("enumerate") == "ok"

    meta = json.loads((sim_root / "meta.json").read_text(encoding="utf-8"))
    assert "1" in meta.get("registry", {})
    assert (vid_dir / "enum" / RUNTIME_ENV_FILE).is_file()


def test_simulate_hit_skips_pipeline(tmp_path: Path) -> None:
    strategy_folder = tmp_path / "demo" / "test_strategy"
    strategy_folder.mkdir(parents=True)
    cached = {
        "enumerate": {
            "success": True,
            "version_id": "2",
            "output_dir": str(strategy_folder / "results" / "simulations" / "2" / "enum"),
        }
    }

    info = MagicMock()
    info.id.return_value = "demo/test_strategy"

    with patch.object(
        strategy_module.DiscoveryService,
        "find_strategy",
        return_value=info,
    ), patch.object(
        strategy_module.DiscoveryService,
        "resolve_strategy_folder",
        return_value=strategy_folder,
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_stock_list",
        return_value=[],
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_latest_completed_trading_date",
        return_value="20240110",
    ), patch.object(
        strategy_module.FingerprintCalculator,
        "calculate_fingerprints",
        return_value=_fps(),
    ), patch.object(
        strategy_module.SimulationVersionStore,
        "get_cache",
        return_value=cached,
    ), patch.object(
        EnumeratorPipeline,
        "run",
    ) as run:
        out = Strategy.simulate("demo/test_strategy", kind=SimulateKind.ENUMERATE)

    assert out["enumerate"] == cached["enumerate"]
    assert out["version_id"] == "2"
    run.assert_not_called()
