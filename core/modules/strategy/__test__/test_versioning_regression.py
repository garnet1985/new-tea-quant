"""Versioning redesign 回归：磁盘 layout + env_invalid + 归因路径。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.consts import (
    EFFECTIVE_SETTINGS_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.simulation_cache.version_store import (
    SimulationVersionStore,
)
from core.modules.strategy.core.strategy import Strategy

pytestmark = pytest.mark.force_run


def _fps(*, settings_fp: str = "sfp", env_fp: str = "efp"):
    return SimpleNamespace(
        settings_fp=settings_fp,
        env_fp=env_fp,
        disk_settings_hash="dsh",
        settings_diff={},
        effective_settings={"core": {"n": 1}},
        entity_ids=["000001.SZ"],
        global_entity_cache=MagicMock(),
    )


def test_registry_hit_requires_matching_env_fp(tmp_path: Path) -> None:
    """环境失效：同 settings、不同 env → 不可 cache hit。"""
    root = tmp_path / "simulations"
    step_dir = root / "1" / "enum"
    step_dir.mkdir(parents=True)
    (step_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    VersionMetaStore.register_version(root, "1", settings_fp="s", env_fp="old-env")

    with patch(
        "core.modules.strategy.core.services.simulation_cache.version_store.ArtifactStore.simulations_root",
        return_value=root,
    ):
        hit = SimulationVersionStore.get_cache(
            tmp_path,
            _fps(settings_fp="s", env_fp="new-env"),
            SimulateKind.ENUMERATE,
        )
    assert hit is None


def test_new_layout_paths_under_shared_version_id(tmp_path: Path) -> None:
    """一个 vid 跨 enum/price/portfolio 子目录。"""
    root = tmp_path / "simulations"
    for step in ("enum", "price", "portfolio"):
        d = root / "4" / step
        d.mkdir(parents=True)
        (d / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    VersionMetaStore.register_version(root, "4", settings_fp="s", env_fp="e")
    VersionMetaStore.write_effective_settings(
        root, "4", settings={"core": {"n": 1}}, entity_ids=["000001.SZ"]
    )

    assert VersionMetaStore.step_has_artifacts(root, "4", SimulateKind.ENUMERATE)
    assert VersionMetaStore.step_has_artifacts(root, "4", SimulateKind.PRICE_FACTOR)
    assert VersionMetaStore.step_has_artifacts(root, "4", SimulateKind.PORTFOLIO)
    assert (root / "4" / EFFECTIVE_SETTINGS_FILE).is_file()
    assert "4" in VersionMetaStore.read_root_meta(root).get("registry", {})


def test_ignore_cache_skips_enum_reuse() -> None:
    from core.modules.strategy.core.engines.enumerator.pipeline import EnumeratorPipeline
    from core.modules.strategy.core.services.simulation_cache.__test__.test_simulate_cache_flow import (
        _ctx,
    )

    ctx = _ctx()
    with patch.object(
        EnumeratorPipeline,
        "find_output_version_via_fps",
        return_value="9",
    ):
        Strategy._resolve_steps(ctx, ignore_cache=True)
    assert ctx.enum_version is None
    assert SimulateKind.ENUMERATE in ctx.steps


def test_effective_settings_snapshot_is_flat_registry(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "2", settings_fp="aa", env_fp="bb")
    meta = VersionMetaStore.read_root_meta(root)
    entry = meta["registry"]["2"]
    assert entry["settings_fp"] == "aa"
    assert entry["env_fp"] == "bb"
    assert "fingerprints" not in entry
    assert "version_id" not in entry
    assert "fingerprint_index" not in meta
