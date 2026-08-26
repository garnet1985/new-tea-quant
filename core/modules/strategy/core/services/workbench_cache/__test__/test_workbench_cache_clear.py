"""Tests for workbench cache clear (V2-11 / V2-12)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.workbench_cache import (
    WorkbenchCacheClear,
)


@patch(
    "core.modules.strategy.core.services.workbench_cache.workbench_cache_clear.DiscoveryService.discover_strategies"
)
def test_clear_all(mock_discover, tmp_path: Path):
    strategy_a = tmp_path / "a"
    strategy_b = tmp_path / "b"
    (strategy_a / "results" / "simulations" / "1").mkdir(parents=True)
    (strategy_b / "results" / "simulations" / "2").mkdir(parents=True)

    info_a = MagicMock()
    info_a.resolved_folder.return_value = strategy_a
    info_b = MagicMock()
    info_b.resolved_folder.return_value = strategy_b
    mock_discover.return_value = [info_a, info_b]

    out = WorkbenchCacheClear.clear_all()
    assert out["ok"] is True
    assert out["deleted_count"] == 2
    assert not (strategy_a / "results" / "simulations").exists()
    assert not (strategy_b / "results" / "simulations").exists()


@patch(
    "core.modules.strategy.core.services.workbench_cache.workbench_cache_clear.DiscoveryService.discover_strategies",
    return_value=[],
)
def test_clear_all_no_strategies(_mock_discover):
    out = WorkbenchCacheClear.clear_all()
    assert out["ok"] is True
    assert out["deleted_count"] == 0


@patch(
    "core.modules.strategy.core.services.workbench_cache.workbench_cache_clear.DiscoveryService.resolve_strategy_folder"
)
def test_clear_by_version_success(mock_resolve, tmp_path: Path):
    strategy_folder = tmp_path / "strategy"
    strategy_folder.mkdir()
    root = strategy_folder / "results" / "simulations"
    version_dir = root / "2" / "enum"
    version_dir.mkdir(parents=True)
    VersionMetaStore.register_version(root, "2", settings_fp="s", env_fp="e")

    mock_resolve.return_value = strategy_folder

    out = WorkbenchCacheClear.clear_by_version("demo/x", 2)
    assert out["ok"] is True
    assert out["deleted"] is True
    assert out["version_id"] == "v2"
    assert not (root / "2").exists()
    assert VersionMetaStore.get_registry_entry(root, "2") is None


@patch(
    "core.modules.strategy.core.services.workbench_cache.workbench_cache_clear.DiscoveryService.resolve_strategy_folder"
)
def test_clear_by_version_missing(mock_resolve, tmp_path: Path):
    strategy_folder = tmp_path / "strategy"
    strategy_folder.mkdir()
    root = strategy_folder / "results" / "simulations"
    root.mkdir(parents=True)

    mock_resolve.return_value = strategy_folder

    out = WorkbenchCacheClear.clear_by_version("demo/x", 9)
    assert out["ok"] is False
    assert out["error"] == "快照不存在"


def test_clear_by_version_invalid_params():
    out = WorkbenchCacheClear.clear_by_version("", 0)
    assert out["ok"] is False
    assert out["error"] == "参数无效"
