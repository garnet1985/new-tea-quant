"""战役 execute / gather：按单层 simulate；旋钮读磁盘有效设置。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.cells import (
    AttributionCell,
    AttributionTask,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.execute import ExecuteStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.gather import (
    GatherStep,
    _compact_summary,
)
from core.modules.strategy.core.enums import SimulateKind
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
        GatherStep,
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
    out = _compact_summary(
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
    assert _compact_summary(SimulateKind.PORTFOLIO, {"win_rate": 0.666667})[
        "win_rate"
    ] == pytest.approx(0.666667)


def test_unique_tasks_share_execute_identity() -> None:
    overlay = AttributionCell(
        index=0,
        overlay={"core": {"rsi_oversold_threshold": 20}},
        runtime_settings={"core": {"rsi_oversold_threshold": 20}},
        execute_settings={"core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}},
        family="overlays",
    )
    matrix_same = AttributionCell(
        index=0,
        overlay={
            "core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}
        },
        runtime_settings={
            "core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}
        },
        execute_settings={"core": {"rsi_oversold_threshold": 20, "max_pe_percentile": 30}},
        family="matrix",
    )
    matrix_other = AttributionCell(
        index=1,
        overlay={
            "core": {"rsi_oversold_threshold": 25, "max_pe_percentile": 30}
        },
        runtime_settings={
            "core": {"rsi_oversold_threshold": 25, "max_pe_percentile": 30}
        },
        execute_settings={"core": {"rsi_oversold_threshold": 25, "max_pe_percentile": 30}},
        family="matrix",
    )
    kind = SimulateKind.PORTFOLIO
    tasks = [
        AttributionTask(cell=overlay, kind=kind, steps=(kind,)),
        AttributionTask(cell=matrix_same, kind=kind, steps=(kind,)),
        AttributionTask(cell=matrix_other, kind=kind, steps=(kind,)),
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
    overlay_bound = ExecuteStep.bind(executed, unique_cells, [overlay])
    assert overlay_bound["cells"][0]["index"] == 0
    assert overlay_bound["cells"][0]["version_id"] == "21"
    matrix_bound = ExecuteStep.bind(
        executed, unique_cells, [matrix_same, matrix_other]
    )
    assert [row["version_id"] for row in matrix_bound["cells"]] == ["21", "21-1"]
