"""战役 execute / gather：按单层 simulate；旋钮读磁盘有效设置。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.plan import (
    AttributionCell,
    AttributionTask,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.execute import ExecuteStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.gather import (
    GatherBase,
    GatherStep,
    compact_summary,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

pytestmark = pytest.mark.force_run


def _task(kind: SimulateKind = SimulateKind.PRICE_FACTOR) -> AttributionTask:
    cell = AttributionCell(
        index=0,
        overlay={"core": {"rsi_oversold_threshold": 20}},
        runtime_settings={"core": {"rsi_oversold_threshold": 20}},
        execute_settings={},
    )
    return AttributionTask(cell=cell, kind=kind, steps=(kind,))


def _payload(kind: SimulateKind, *, hit: bool, version_id: str = "21-1") -> dict:
    return {
        "cache_hit": hit,
        "version_id": version_id,
        kind.value: {"version_id": version_id, "output_dir": f"/tmp/{version_id}"},
    }


def test_from_cells_steps_include_upstream() -> None:
    from core.modules.strategy.core.engines.analyzer.steps.campaign.plan import (
        simulate_steps_for_kind,
    )

    assert simulate_steps_for_kind(SimulateKind.ENUMERATE) == (
        SimulateKind.ENUMERATE,
    )
    assert simulate_steps_for_kind(SimulateKind.PRICE_FACTOR) == (
        SimulateKind.ENUMERATE,
        SimulateKind.PRICE_FACTOR,
    )
    assert simulate_steps_for_kind(SimulateKind.PORTFOLIO) == (
        SimulateKind.ENUMERATE,
        SimulateKind.PRICE_FACTOR,
        SimulateKind.PORTFOLIO,
    )
    cell = AttributionCell(
        index=0,
        overlay={},
        runtime_settings={},
        execute_settings={},
    )
    tasks = AttributionTask.from_cells([cell], kind=SimulateKind.PORTFOLIO)
    assert tasks[0].steps == (
        SimulateKind.ENUMERATE,
        SimulateKind.PRICE_FACTOR,
        SimulateKind.PORTFOLIO,
    )


def test_simulate_price_chain_force_only_first_step() -> None:
    """spa：steps=枚举→价格；-f 只打在第一层。"""
    info = MagicMock()
    info.key = "demo/rsi"
    calls = []

    def fake_simulate(key, *, kind, ignore_cache, runtime_settings, version_id=None):
        calls.append((kind, ignore_cache, version_id))
        return _payload(kind, hit=False)

    fp = SimpleNamespace(execute_fp="e-overlay", env_fp="n")
    cell = AttributionCell(
        index=0,
        overlay={"core": {"rsi_oversold_threshold": 20}},
        runtime_settings={"core": {"rsi_oversold_threshold": 20}},
        execute_settings={},
    )
    task = AttributionTask.from_cells([cell], kind=SimulateKind.PRICE_FACTOR)[0]
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ), patch.object(
        VersionMetaStore, "allocate_replica_id", return_value="21-1"
    ):
        result = ExecuteStep._simulate(
            MagicMock(),
            info,
            task,
            parent_version_id="21",
            baseline_execute_fp="e-baseline",
            ignore_cache=True,
        )
    assert [(kind, force) for kind, force, _vid in calls] == [
        (SimulateKind.ENUMERATE, True),
        (SimulateKind.PRICE_FACTOR, False),
    ]
    assert result.status == "simulated"
    assert result.version_id == "21-1"


def test_price_gap_reuses_existing_enum(tmp_path) -> None:
    """只改近邻间隔时读已有枚举，不再为这一格跑枚举。"""
    root = tmp_path / "sim"
    primary = root / "21"
    other = root / "21-1"
    primary.mkdir(parents=True)
    other.mkdir()
    (root / "meta.json").write_text(
        """{
          "registry": {
            "21": {"steps": {"enumerate": "ok"}},
            "21-1": {"steps": {"enumerate": "ok"}}
          }
        }""",
        encoding="utf-8",
    )
    (primary / "effective_settings.json").write_text(
        """{
          "core": {"rsi_oversold_threshold": 30},
          "simulation": {"price": {"opportunity_merge_gap": 1}}
        }""",
        encoding="utf-8",
    )
    (other / "effective_settings.json").write_text(
        """{
          "core": {"rsi_oversold_threshold": 20},
          "simulation": {"price": {"opportunity_merge_gap": 1}}
        }""",
        encoding="utf-8",
    )
    cell = AttributionCell(
        index=2,
        overlay={"simulation": {"price": {"opportunity_merge_gap": 3}}},
        runtime_settings={"simulation": {"price": {"opportunity_merge_gap": 3}}},
        execute_settings={
            "core": {"rsi_oversold_threshold": 30},
            "simulation": {"price": {"opportunity_merge_gap": 3}},
        },
    )
    task = AttributionTask.from_cells([cell], kind=SimulateKind.PRICE_FACTOR)[0]
    info = MagicMock()
    info.key = "demo/rsi"
    calls = []

    def fake_simulate(
        key,
        *,
        kind,
        ignore_cache,
        runtime_settings,
        version_id=None,
        upstream_version_id=None,
    ):
        calls.append((kind, version_id, upstream_version_id, ignore_cache))
        return _payload(kind, hit=False, version_id=str(version_id))

    fp = SimpleNamespace(execute_fp="e-gap", env_fp="n")
    with patch.object(
        ArtifactStore, "simulations_root", return_value=root
    ), patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ), patch.object(
        VersionMetaStore, "allocate_replica_id", return_value="21-2"
    ):
        result = ExecuteStep._simulate(
            tmp_path,
            info,
            task,
            parent_version_id="21",
            baseline_execute_fp="e-baseline",
            ignore_cache=False,
        )
    assert calls == [
        (SimulateKind.PRICE_FACTOR, "21-2", "21", False),
    ]
    assert result.status == "simulated"
    assert result.version_id == "21-2"


def test_simulate_single_layer_force_on_first() -> None:
    info = MagicMock()
    info.key = "demo/rsi"
    calls = []

    def fake_simulate(key, *, kind, ignore_cache, runtime_settings, version_id=None):
        calls.append((kind, ignore_cache, dict(runtime_settings), version_id))
        return _payload(kind, hit=True)

    fp = SimpleNamespace(execute_fp="e-overlay", env_fp="n")
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ), patch.object(
        VersionMetaStore, "allocate_replica_id", return_value="21-1"
    ):
        result = ExecuteStep._simulate(
            MagicMock(),
            info,
            _task(SimulateKind.PRICE_FACTOR),
            parent_version_id="21",
            baseline_execute_fp="e-baseline",
            ignore_cache=True,
        )
    assert [(kind, force, vid) for kind, force, _, vid in calls] == [
        (SimulateKind.PRICE_FACTOR, True, "21-1"),
    ]
    assert all(
        runtime == {"core": {"rsi_oversold_threshold": 20}}
        for _, _, runtime, _ in calls
    )
    assert result.status == "hit"
    assert result.version_id == "21-1"


def test_allocation_variant_reuses_upstream_and_skips_enum() -> None:
    info = MagicMock()
    info.key = "demo/rsi"
    calls = []

    def fake_simulate(
        key,
        *,
        kind,
        ignore_cache,
        runtime_settings,
        version_id=None,
        upstream_version_id=None,
    ):
        calls.append((kind, version_id, upstream_version_id, runtime_settings))
        return _payload(kind, hit=False, version_id=str(version_id))

    cell = AttributionCell(
        index=1,
        overlay={"portfolio": {"allocation": {"max_portfolio_size": 20}}},
        runtime_settings={"portfolio": {"allocation": {"max_portfolio_size": 20}}},
        execute_settings={},
        family="allocation",
    )
    task = AttributionTask(
        cell=cell, kind=SimulateKind.PORTFOLIO, steps=(SimulateKind.PORTFOLIO,)
    )
    fp = SimpleNamespace(execute_fp="e-alloc", env_fp="n")
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ), patch.object(
        VersionMetaStore,
        "allocate_replica_id",
        return_value="9-1",
    ):
        result = ExecuteStep._simulate(
            MagicMock(),
            info,
            task,
            parent_version_id="9",
            baseline_execute_fp="e-baseline",
            ignore_cache=False,
        )
    assert calls == [
        (
            SimulateKind.PORTFOLIO,
            "9-1",
            "9",
            {"portfolio": {"allocation": {"max_portfolio_size": 20}}},
        )
    ]
    assert result.version_id == "9-1"
    assert result.status == "simulated"


def test_allocation_baseline_stays_on_primary() -> None:
    info = MagicMock()
    info.key = "demo/rsi"
    calls = []

    def fake_simulate(
        key,
        *,
        kind,
        ignore_cache,
        runtime_settings,
        version_id=None,
        upstream_version_id=None,
    ):
        calls.append((kind, version_id, upstream_version_id))
        return _payload(kind, hit=True, version_id="9")

    cell = AttributionCell(
        index=0,
        overlay={},
        runtime_settings={},
        execute_settings={},
        family="allocation",
    )
    task = AttributionTask(
        cell=cell, kind=SimulateKind.PORTFOLIO, steps=(SimulateKind.PORTFOLIO,)
    )
    fp = SimpleNamespace(execute_fp="e-baseline", env_fp="n")
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ):
        result = ExecuteStep._simulate(
            MagicMock(),
            info,
            task,
            parent_version_id="9",
            baseline_execute_fp="e-baseline",
            ignore_cache=False,
        )
    assert calls == [(SimulateKind.PORTFOLIO, "9", "9")]
    assert result.status == "hit"
    assert result.version_id == "9"


def test_simulate_baseline_reuses_primary() -> None:
    info = MagicMock()
    info.key = "demo/rsi"
    calls = []

    def fake_simulate(key, *, kind, ignore_cache, runtime_settings, version_id=None):
        calls.append(version_id)
        return _payload(kind, hit=True, version_id="21")

    fp = SimpleNamespace(execute_fp="e-baseline", env_fp="n")
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ):
        result = ExecuteStep._simulate(
            MagicMock(),
            info,
            _task(SimulateKind.ENUMERATE),
            parent_version_id="21",
            baseline_execute_fp="e-baseline",
            ignore_cache=False,
        )
    assert calls == ["21"]
    assert result.version_id == "21"
    assert result.status == "hit"


def test_simulate_status_simulated_on_miss() -> None:
    info = MagicMock()
    info.key = "demo/rsi"

    def fake_simulate(key, *, kind, ignore_cache, runtime_settings, version_id=None):
        return _payload(kind, hit=False, version_id=version_id or "21-2")

    fp = SimpleNamespace(execute_fp="e-overlay", env_fp="n")
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ), patch.object(
        VersionMetaStore, "allocate_replica_id", return_value="21-2"
    ):
        result = ExecuteStep._simulate(
            MagicMock(),
            info,
            _task(SimulateKind.PORTFOLIO),
            parent_version_id="21",
            baseline_execute_fp="e-baseline",
            ignore_cache=False,
        )
    assert result.status == "simulated"
    assert result.version_id == "21-2"


def test_gather_knobs_prefer_disk_effective(tmp_path, monkeypatch) -> None:
    cell = AttributionCell(
        index=0,
        overlay={
            "core": {"max_pe_percentile": 20},
            "goal": {"stop_loss": None},
        },
        runtime_settings={
            "core": {"max_pe_percentile": 20},
            "goal": {"stop_loss": None},
        },
        execute_settings={},
    )
    task = AttributionTask(
        cell=cell, kind=SimulateKind.PORTFOLIO, steps=(SimulateKind.PORTFOLIO,)
    )
    monkeypatch.setattr(
        VersionMetaStore,
        "read_effective_settings",
        classmethod(
            lambda cls, root, vid: {
                "core": {
                    "rsi_oversold_threshold": 20,
                    "max_pe_percentile": 99,
                    "min_netprofit_yoy": 0,
                },
                "goal": {"stop_loss": None},
            }
            if vid == "21"
            else None
        ),
    )
    monkeypatch.setattr(
        GatherBase,
        "_load_layers",
        classmethod(
            lambda cls, folder, vid: {
                "enumerate": {"total_opportunities": 18},
                "price_factor": {"win_rate": 0.5, "avg_roi": 0.01},
                "portfolio": {"total_return": 0.07},
            }
        ),
    )
    out = GatherStep.run(
        tmp_path,
        [task],
        {"cells": [{"index": 0, "status": "hit", "version_id": "21"}]},
    )
    knobs = out["rows"][0]["knobs"]
    assert knobs["core.max_pe_percentile"] == 99
    assert knobs["goal.stop_loss"] is None
    assert out["rows"][0]["layers"]["price_factor"]["win_rate"] == 0.5


def test_price_factor_win_rate_percent_becomes_ratio() -> None:
    out = compact_summary(
        SimulateKind.PRICE_FACTOR,
        {
            "win_rate": 72.2,
            "avg_roi": 0.1121,
            "total_completed_investments": 18,
            "total_profit": 238.74,
        },
    )
    assert out["win_rate"] == pytest.approx(0.722)
    assert out["avg_roi"] == 0.1121
    assert out["total_completed_investments"] == 18
    assert compact_summary(SimulateKind.PORTFOLIO, {"win_rate": 0.666667})[
        "win_rate"
    ] == pytest.approx(0.666667)


def test_unique_tasks_share_execute_identity() -> None:
    cell_a = AttributionCell(
        index=0,
        overlay={"core": {"rsi_oversold_threshold": 20}},
        runtime_settings={"core": {"rsi_oversold_threshold": 20}},
        execute_settings={
            "core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}
        },
        family="inputs",
    )
    cell_same = AttributionCell(
        index=1,
        overlay={
            "core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}
        },
        runtime_settings={
            "core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}
        },
        execute_settings={
            "core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}
        },
        family="inputs",
    )
    cell_other = AttributionCell(
        index=2,
        overlay={
            "core": {"rsi_oversold_threshold": 25, "max_pe_percentile": 30}
        },
        runtime_settings={
            "core": {"rsi_oversold_threshold": 25, "max_pe_percentile": 30}
        },
        execute_settings={
            "core": {"rsi_oversold_threshold": 25, "max_pe_percentile": 30}
        },
        family="inputs",
    )
    kind = SimulateKind.PORTFOLIO
    tasks = [
        AttributionTask(cell=cell_a, kind=kind, steps=(kind,)),
        AttributionTask(cell=cell_same, kind=kind, steps=(kind,)),
        AttributionTask(cell=cell_other, kind=kind, steps=(kind,)),
    ]
    unique = ExecuteStep.unique_tasks(tasks)
    assert len(unique) == 2
    executed = {
        "status": "ok",
        "cells": [
            {"index": 0, "status": "hit", "version_id": "21"},
            {"index": 1, "status": "simulated", "version_id": "21-1"},
        ],
    }
    unique_cells = [task.cell for task in unique]
    bound_a = ExecuteStep.bind(executed, unique_cells, [cell_a])
    assert bound_a["cells"][0]["index"] == 0
    assert bound_a["cells"][0]["version_id"] == "21"
    bound_b = ExecuteStep.bind(
        executed, unique_cells, [cell_same, cell_other]
    )
    assert [row["version_id"] for row in bound_b["cells"]] == ["21", "21-1"]
