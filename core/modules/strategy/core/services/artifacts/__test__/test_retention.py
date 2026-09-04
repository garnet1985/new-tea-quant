"""ArtifactRetention：keep-N prune 与显式删除。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.services.artifacts import ArtifactRetention, ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

pytestmark = pytest.mark.force_run

_DISCOVER = (
    "core.modules.strategy.core.services.artifacts.retention.DiscoveryService.discover_strategies"
)
_RESOLVE = (
    "core.modules.strategy.core.services.artifacts.retention.DiscoveryService.resolve_strategy_folder"
)


def test_prune_simulation_results_per_kind(tmp_path: Path) -> None:
    sim_root = tmp_path / "simulations"
    for i in (1, 2, 3, 4):
        (sim_root / str(i) / "enum").mkdir(parents=True)

    with patch.object(
        ArtifactRetention,
        "_resolve_folder",
        return_value=tmp_path,
    ), patch.object(
        ArtifactStore,
        "simulations_root",
        classmethod(lambda cls, folder: sim_root),
    ):
        out = ArtifactRetention.prune_simulation_results(
            "demo/x", kind="enum", max_versions=2
        )

    assert out["ok"] is True
    assert out["deleted_count"] == 2
    assert out["per_kind"]["enumerate"] == 2
    remaining = sorted(
        int(p.name) for p in sim_root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == [3, 4]


def test_prune_scan_results_keeps_newest_dates(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    for day in ("20240108", "20240109", "20240110"):
        (scan_root / day).mkdir(parents=True)

    with patch.object(
        ArtifactRetention,
        "_resolve_folder",
        return_value=tmp_path,
    ), patch.object(
        ArtifactStore,
        "scan_root",
        classmethod(lambda cls, folder: scan_root),
    ):
        out = ArtifactRetention.prune_scan_results("demo/x", max_versions=2)

    assert out["ok"] is True
    assert out["deleted_count"] == 1
    assert out["max_versions"] == 2
    remaining = sorted(p.name for p in scan_root.iterdir() if p.is_dir())
    assert remaining == ["20240109", "20240110"]


def test_retention_does_not_import_engines() -> None:
    import core.modules.strategy.core.services.artifacts.retention as mod

    text = Path(mod.__file__).read_text(encoding="utf-8")
    assert "engines" not in text
    assert "ScanCacheManager" not in text


def test_prune_rejects_unknown_kind(tmp_path: Path) -> None:
    with patch.object(ArtifactRetention, "_resolve_folder", return_value=tmp_path):
        with pytest.raises(ValueError, match="unsupported"):
            ArtifactRetention.prune_simulation_results("demo/x", kind="full")


@patch(_DISCOVER)
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

    out = ArtifactRetention.clear_all()
    assert out["ok"] is True
    assert out["deleted_count"] == 2
    assert not (strategy_a / "results" / "simulations").exists()
    assert not (strategy_b / "results" / "simulations").exists()


@patch(_DISCOVER, return_value=[])
def test_clear_all_no_strategies(_mock_discover):
    out = ArtifactRetention.clear_all()
    assert out["ok"] is True
    assert out["deleted_count"] == 0


@patch(_RESOLVE)
def test_clear_by_version_success(mock_resolve, tmp_path: Path):
    strategy_folder = tmp_path / "strategy"
    strategy_folder.mkdir()
    root = strategy_folder / "results" / "simulations"
    version_dir = root / "2" / "enum"
    version_dir.mkdir(parents=True)
    VersionMetaStore.register_version(root, "2", execute_fp="s", env_fp="e")

    mock_resolve.return_value = strategy_folder

    out = ArtifactRetention.clear_by_version("demo/x", 2)
    assert out["ok"] is True
    assert out["deleted"] is True
    assert out["version_id"] == "v2"
    assert out.get("was_pinned") is False
    assert not (root / "2").exists()
    assert VersionMetaStore.get_registry_entry(root, "2") is None


@patch(_RESOLVE)
def test_clear_by_version_reports_was_pinned(mock_resolve, tmp_path: Path):
    strategy_folder = tmp_path / "strategy"
    strategy_folder.mkdir()
    root = strategy_folder / "results" / "simulations"
    (root / "2").mkdir(parents=True)
    VersionMetaStore.register_version(root, "2", execute_fp="s", env_fp="e")
    VersionMetaStore.set_version_pinned(root, "2", True)
    mock_resolve.return_value = strategy_folder

    out = ArtifactRetention.clear_by_version("demo/x", 2)
    assert out["ok"] is True
    assert out["was_pinned"] is True
    assert VersionMetaStore.read_pinned_ids(root) == []


@patch(_RESOLVE)
def test_set_pinned_roundtrip(mock_resolve, tmp_path: Path):
    strategy_folder = tmp_path / "strategy"
    strategy_folder.mkdir()
    root = strategy_folder / "results" / "simulations"
    (root / "3").mkdir(parents=True)
    VersionMetaStore.register_version(root, "3", execute_fp="s", env_fp="e")
    mock_resolve.return_value = strategy_folder

    out = ArtifactRetention.set_pinned("demo/x", 3, True)
    assert out["ok"] is True
    assert out["pinned"] is True
    assert out["pinned_ids"] == ["v3"]
    assert VersionMetaStore.read_pinned_ids(root) == ["3"]
    out = ArtifactRetention.set_pinned("demo/x", 3, False)
    assert out["pinned"] is False
    assert out["pinned_ids"] == []


@patch(_RESOLVE)
def test_clear_by_version_missing(mock_resolve, tmp_path: Path):
    strategy_folder = tmp_path / "strategy"
    strategy_folder.mkdir()
    root = strategy_folder / "results" / "simulations"
    root.mkdir(parents=True)

    mock_resolve.return_value = strategy_folder

    out = ArtifactRetention.clear_by_version("demo/x", 9)
    assert out["ok"] is False
    assert out["error"] == "快照不存在"


def test_clear_by_version_invalid_params():
    out = ArtifactRetention.clear_by_version("", 0)
    assert out["ok"] is False
    assert out["error"] == "参数无效"
