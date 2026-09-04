"""归因并进 report 步：Pipeline 离开时 report 仍 open，analyze 之后才 complete。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.progress import (
    PipelineProgress,
    ProgressRecorder,
)
from core.modules.strategy.core.strategy import Strategy
import core.modules.strategy.core.strategy as strategy_mod

pytestmark = pytest.mark.force_run


def _patch_recorder(tmp_path, monkeypatch):
    def _build(channel, file_key):
        return tmp_path / "progress" / channel / f"{file_key}.json"

    monkeypatch.setattr(ProgressRecorder, "build_path", staticmethod(_build))


class _FakePipeline:
    @staticmethod
    def run(_ctx):
        for name in ("load", "dispatch", "execute"):
            PipelineProgress.enter_step_bound(name)
            PipelineProgress.complete_step_bound(name)
        PipelineProgress.enter_step_bound("report")
        return {
            "success": True,
            "version_id": "1",
            "output_dir": "/tmp/demo",
        }


def test_run_steps_completes_report_after_analysis(tmp_path, monkeypatch):
    _patch_recorder(tmp_path, monkeypatch)
    monkeypatch.setattr(
        strategy_mod.BackTestPipelines,
        "__class_getitem__",
        classmethod(lambda cls, kind: _FakePipeline),
    )
    monkeypatch.setattr(
        strategy_mod.SimulationVersionStore,
        "record_step_complete",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        strategy_mod.StrategySettings,
        "extract_execute_settings",
        lambda _settings: {},
    )

    seen = {}

    def _fake_analysis(step, step_res, ctx, folder, *, force=False):
        cur = PipelineProgress.current()
        assert cur is not None
        doc = cur.to_dict()
        seen["step"] = (doc.get("step") or {}).get("name")
        seen["progress"] = float(doc.get("progress") or 0.0)
        return {"skipped": True, "reason": "disabled"}

    monkeypatch.setattr(Strategy, "_maybe_run_analysis", staticmethod(_fake_analysis))

    ctx = MagicMock()
    ctx.steps = [SimulateKind.ENUMERATE]
    ctx.kind = SimulateKind.ENUMERATE
    ctx.strategy_key = "demo/x"
    ctx.entity_ids = []
    ctx.fp_res = MagicMock()
    ctx.effective_settings = MagicMock()
    ctx.enum_version = None

    PipelineProgress.seed("demo/x", "job1", pipeline_name="enum")
    with PipelineProgress.bind("demo/x", "job1"):
        PipelineProgress.mark_running_bound()
        Strategy._run_steps(ctx, strategy_folder=tmp_path)
        after = PipelineProgress.current().to_dict()

    assert seen["step"] == "report"
    assert seen["progress"] < 100.0
    assert after["step"] is None
    assert [x["name"] for x in after["completed_steps"]] == [
        "load",
        "dispatch",
        "execute",
        "report",
    ]
    assert float(after["progress"]) == 100.0
