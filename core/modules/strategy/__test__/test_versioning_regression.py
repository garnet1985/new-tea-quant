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
    SCOPE_FILE,
    SETTINGS_FILE,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.artifacts import ArtifactStore, SimulationVersionStore
from core.modules.strategy.core.strategy import Strategy

pytestmark = pytest.mark.force_run


def _fps(*, execute_fp: str = "sfp", env_fp: str = "efp"):
    settings = MagicMock()
    settings.analysis.enabled = False
    return SimpleNamespace(
        execute_fp=execute_fp,
        env_fp=env_fp,
        settings_diff={},
        effective_settings=settings,
        entity_ids=["000001.SZ"],
    )


def test_registry_hit_requires_matching_env_fp(tmp_path: Path) -> None:
    """环境失效：同 settings、不同 env → 不可 cache hit。"""
    root = tmp_path / "simulations"
    step_dir = root / "1" / "enum"
    step_dir.mkdir(parents=True)
    (step_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    VersionMetaStore.register_version(root, "1", execute_fp="s", env_fp="old-env")

    with patch.object(ArtifactStore, "simulations_root", return_value=root):
        hit = SimulationVersionStore.get_cache(
            tmp_path,
            _fps(execute_fp="s", env_fp="new-env"),
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
    VersionMetaStore.register_version(root, "4", execute_fp="s", env_fp="e")
    VersionMetaStore.write_version_archive(
        root,
        "4",
        full_settings={"meta": {"key": "demo"}, "core": {"n": 1}},
        effective_settings={"core": {"n": 1}},
        entity_ids=["000001.SZ"],
        start_date="20240102",
        end_date="20240110",
    )

    assert VersionMetaStore.step_has_artifacts(root, "4", SimulateKind.ENUMERATE)
    assert VersionMetaStore.step_has_artifacts(root, "4", SimulateKind.PRICE_FACTOR)
    assert VersionMetaStore.step_has_artifacts(root, "4", SimulateKind.PORTFOLIO)
    assert (root / "4" / SETTINGS_FILE).is_file()
    assert (root / "4" / EFFECTIVE_SETTINGS_FILE).is_file()
    assert (root / "4" / SCOPE_FILE).is_file()
    effective = json.loads((root / "4" / EFFECTIVE_SETTINGS_FILE).read_text(encoding="utf-8"))
    assert "entity_ids" not in effective
    assert "4" in VersionMetaStore.read_root_meta(root).get("registry", {})


def test_ignore_cache_skips_enum_reuse() -> None:
    from core.modules.strategy.core.engines.enumerator.pipeline import EnumeratorPipeline
    from core.modules.strategy.__test__.test_simulate_cache_flow import (
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


def test_overwrite_enum_clears_downstream_artifacts(tmp_path: Path) -> None:
    """D18：同 vid 复写 enum 时删除 price / portfolio 产物。"""
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "6", execute_fp="sfp", env_fp="efp")
    for name, kind in (
        ("enum", SimulateKind.ENUMERATE),
        ("price", SimulateKind.PRICE_FACTOR),
        ("portfolio", SimulateKind.PORTFOLIO),
    ):
        d = root / "6" / name
        d.mkdir(parents=True)
        (d / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
        VersionMetaStore.mark_step_complete(root, "6", kind)

    VersionMetaStore.clear_downstream_steps(root, "6", SimulateKind.ENUMERATE)
    assert VersionMetaStore.step_has_artifacts(root, "6", SimulateKind.ENUMERATE)
    assert not VersionMetaStore.step_has_artifacts(root, "6", SimulateKind.PRICE_FACTOR)
    assert not VersionMetaStore.step_has_artifacts(root, "6", SimulateKind.PORTFOLIO)


def test_enum_report_manager_begin_reuses_fingerprint_vid(tmp_path: Path, monkeypatch) -> None:
    """D17：同指纹重跑枚举写入同一 vid；begin 不得把 VersionMetaStore 变成局部变量。"""
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )
    from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
        StrategySettings,
    )
    from core.modules.strategy.core.services.artifacts import ArtifactStore, EnumerateStore

    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "6", execute_fp="sfp", env_fp="efp")
    monkeypatch.setattr(
        ArtifactStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    monkeypatch.setattr(
        EnumerateStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    settings = StrategySettings.from_dict(
        {
            "core": {"n": 1},
            "simulation": {
                "execution": {
                    "mode": "entity_based",
                    "start_date": "20240102",
                    "end_date": "20240110",
                }
            },
        }
    )
    mgr = ReportManager.begin(
        "demo",
        entity_ids=["000001.SZ"],
        execute_fp="sfp",
        env_fp="efp",
        effective_settings=settings,
        settings_diff={},
        execution_mode="entity_based",
        market_profile="cn",
        strategy_path="demo",
        strategy_folder=tmp_path,
    )
    assert int(mgr.version_id) == 6
    assert mgr.output_dir == root / "6" / "enum"


def test_run_steps_clears_downstream_before_overwriting_enum(tmp_path: Path) -> None:
    from core.modules.strategy.__test__.test_simulate_cache_flow import _ctx
    from core.modules.strategy.core.services.artifacts import ArtifactStore

    ctx = _ctx(kind=SimulateKind.ENUMERATE)
    ctx.steps = [SimulateKind.ENUMERATE]
    pipeline = MagicMock()
    pipeline.run.return_value = {
        "success": True,
        "version_id": "6",
        "output_dir": str(tmp_path / "6" / "enum"),
    }
    with patch.object(
        ArtifactStore, "simulations_root", return_value=tmp_path / "simulations"
    ), patch.object(
        VersionMetaStore, "find_version_by_fingerprints", return_value="6"
    ), patch.object(
        VersionMetaStore, "step_status", return_value="ok"
    ), patch.object(
        VersionMetaStore, "clear_downstream_steps"
    ) as clear, patch.object(
        ArtifactStore, "clear_cache"
    ), patch.object(
        SimulationVersionStore, "record_step_complete"
    ), patch.object(
        Strategy, "_maybe_run_analysis", return_value=None
    ), patch(
        "core.modules.strategy.core.services.progress.PipelineProgress.complete_step_bound"
    ), patch(
        "core.modules.strategy.core.strategy.BackTestPipelines.__class_getitem__",
        return_value=pipeline,
    ):
        Strategy._run_steps(ctx, strategy_folder=tmp_path, ignore_cache=True)

    clear.assert_called_once()
    assert clear.call_args.args[1] == "6"
    assert clear.call_args.args[2] == SimulateKind.ENUMERATE
    pipeline.run.assert_called_once()


def test_effective_settings_snapshot_is_flat_registry(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "2", execute_fp="aa", env_fp="bb")
    meta = VersionMetaStore.read_root_meta(root)
    entry = meta["registry"]["2"]
    assert entry["execute_fp"] == "aa"
    assert entry["env_fp"] == "bb"
    assert "fingerprints" not in entry
    assert "version_id" not in entry
    assert "fingerprint_index" not in meta
