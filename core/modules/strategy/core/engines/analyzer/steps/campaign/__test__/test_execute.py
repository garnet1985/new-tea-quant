"""战役 execute / gather：按 steps 逐层 simulate；旋钮读磁盘有效设置。"""
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

_STEPS = (
    SimulateKind.ENUMERATE,
    SimulateKind.PRICE_FACTOR,
    SimulateKind.PORTFOLIO,
)


def _task() -> AttributionTask:
    cell = AttributionCell(
        index=0,
        overlay={"core": {"rsi_oversold_threshold": 20}},
        runtime_settings={"core": {"rsi_oversold_threshold": 20}},
        execute_settings={},
    )
    return AttributionTask(cell=cell, kind=SimulateKind.PORTFOLIO, steps=_STEPS)


def _payload(kind: SimulateKind, *, hit: bool) -> dict:
    return {
        "cache_hit": hit,
        "version_id": "21",
        kind.value: {"version_id": "21", "output_dir": "/tmp/v21"},
    }


def test_simulate_each_declared_step_force_only_first() -> None:
    info = MagicMock()
    info.key = "demo/rsi"
    calls = []

    def fake_simulate(key, *, kind, ignore_cache, runtime_settings):
        calls.append((kind, ignore_cache, dict(runtime_settings)))
        return _payload(kind, hit=True)

    fp = SimpleNamespace(execute_fp="e", env_fp="n")
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ):
        result = ExecuteStep._simulate(info, _task(), ignore_cache=True)
    assert [(kind, force) for kind, force, _ in calls] == [
        (SimulateKind.ENUMERATE, True),
        (SimulateKind.PRICE_FACTOR, False),
        (SimulateKind.PORTFOLIO, False),
    ]
    assert all(
        runtime == {"core": {"rsi_oversold_threshold": 20}}
        for _, _, runtime in calls
    )
    assert result.status == "hit"
    assert result.version_id == "21"


def test_simulate_status_simulated_when_price_layer_misses() -> None:
    info = MagicMock()
    info.key = "demo/rsi"
    hits = {
        SimulateKind.ENUMERATE: True,
        SimulateKind.PRICE_FACTOR: False,
        SimulateKind.PORTFOLIO: True,
    }

    def fake_simulate(key, *, kind, ignore_cache, runtime_settings):
        return _payload(kind, hit=hits[kind])

    fp = SimpleNamespace(execute_fp="e", env_fp="n")
    with patch.object(ExecuteStep, "_fingerprints", return_value=fp), patch(
        "core.modules.strategy.core.strategy.Strategy.simulate",
        side_effect=fake_simulate,
    ):
        result = ExecuteStep._simulate(info, _task(), ignore_cache=False)
    assert result.status == "simulated"
    assert result.version_id == "21"


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
        cell=cell, kind=SimulateKind.PORTFOLIO, steps=_STEPS
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
