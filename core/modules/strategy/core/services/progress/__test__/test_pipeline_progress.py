"""Tests for PipelineProgress service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.modules.strategy.core.services.progress import PipelineProgress


@pytest.fixture(autouse=True)
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path / "progress"))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    from core.infra.progress.core import store

    store.reset()
    yield tmp_path
    store.reset()


def test_seed_enter_tick_complete():
    PipelineProgress.seed("demo/x", "job1", pipeline_name="enum")

    with PipelineProgress.bind("demo/x", "job1") as prog:
        prog.mark_running()
        prog.enter_step("load")
        prog.complete_step("load")
        prog.enter_step("dispatch")
        prog.complete_step("dispatch")
        prog.enter_step("execute")
        prog.tick_execute(5, 10)
        assert prog.to_dict()["step"]["counters"] == {"done": 5, "total": 10}
        mid = float(prog.to_dict()["progress"])
        assert 0 < mid < 100
        prog.tick_execute(10, 10)
        prog.complete_step("execute")
        prog.enter_step("report")
        prog.complete_step("report")
        prog.complete(result={"version_id": "v3"})

    doc = PipelineProgress.get("demo/x", "job1")
    assert doc is not None
    assert doc["status"] == "completed"
    assert doc["progress"] == 100.0
    assert doc["result"]["version_id"] == "v3"
    names = [x["name"] for x in doc["completed_steps"]]
    assert names == ["load", "dispatch", "execute", "report"]


def test_report_step_stays_open_until_complete():
    """归因并进 report：complete 之前当前步仍是 report，总进度未到 100。"""
    PipelineProgress.seed("demo/x", "job-report", pipeline_name="enum")
    with PipelineProgress.bind("demo/x", "job-report") as prog:
        prog.mark_running()
        for name in ("load", "dispatch", "execute"):
            prog.enter_step(name)
            prog.complete_step(name)
        prog.enter_step("report")
        mid = prog.to_dict()
        assert mid["step"]["name"] == "report"
        assert float(mid["progress"]) < 100.0
        prog.complete_step("report")
        done = prog.to_dict()
        assert done["step"] is None
        assert float(done["progress"]) == 100.0


def test_fail_keeps_completed_steps():
    PipelineProgress.seed("demo/x", "job2", pipeline_name="price")
    with PipelineProgress.bind("demo/x", "job2") as prog:
        prog.mark_running()
        prog.enter_step("load")
        prog.complete_step()
        prog.enter_step("execute")
        prog.tick_execute(1, 4)
        prog.fail("boom")

    doc = PipelineProgress.get("demo/x", "job2")
    assert doc["status"] == "failed"
    assert doc["error"] == "boom"
    assert doc["completed_steps"][0]["name"] == "load"
    assert doc["step"]["name"] == "execute"


def test_stale_running_marked_failed():
    import json

    from core.modules.strategy.core.services.progress import ProgressRecorder

    PipelineProgress.seed("demo/x", "job3", pipeline_name="enum")
    with PipelineProgress.bind("demo/x", "job3") as prog:
        prog.mark_running()
        prog.enter_step("execute")
        path = ProgressRecorder.for_strategy_workbench_run(
            "demo/x", "job3"
        ).recorder_path
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        path.write_text(json.dumps(raw), encoding="utf-8")

    doc = PipelineProgress.get("demo/x", "job3", apply_stale=True)
    assert doc["status"] == "failed"
    assert "超时" in doc["error"]


def test_bound_facades_noop_without_bind():
    PipelineProgress.enter_step_bound("load")
    PipelineProgress.tick_execute_bound(1, 2)
    assert PipelineProgress.current() is None


def test_attribute_pipeline_uses_shared_steps():
    """归因跳过调度，三步等权。对照回测的子步骤加在当前步上。"""
    from core.modules.strategy.core.services.progress import ATTRIBUTE_PIPELINE
    from core.infra.progress import Progress

    PipelineProgress.seed(
        "demo/x",
        "job-attr",
        pipeline_name=ATTRIBUTE_PIPELINE,
        pipeline_description="枚举归因",
    )
    with PipelineProgress.bind("demo/x", "job-attr") as prog:
        prog.mark_running()
        prog.enter_step("load")
        assert prog.to_dict()["step"]["description"] == "准备任务"
        prog.complete_step("load")
        assert float(prog.to_dict()["progress"]) == 33.33

        prog.enter_step("execute")
        prog.tick_execute(1, 4)
        # (1 + 1/4) / 3
        assert float(prog.to_dict()["progress"]) == 41.67

        shared = Progress.read("pipeline-demo-x-job-attr")
        assert shared["job"] == "attribute"
        assert shared["ratio"] == 0.4167
        assert shared["steps"][1]["done"] == 1
        assert shared["steps"][1]["total"] == 4
        assert prog.to_dict()["step"]["counters"] == {"done": 1, "total": 4}
        assert prog.to_dict()["step"]["description"] == "对照回测"

        assert PipelineProgress.drives_pipeline("enum") is False
        assert PipelineProgress.drives_pipeline(ATTRIBUTE_PIPELINE) is True

        prog.tick_execute(4, 4)
        prog.complete_step("execute")
        prog.enter_step("report")
        assert prog.to_dict()["step"]["description"] == "归因与报告"
        assert float(prog.to_dict()["progress"]) == 66.67
        prog.complete_step("report")
        assert float(prog.to_dict()["progress"]) == 100.0


def test_rolling_tick_keeps_window_step_label():
    """滚动对照一次只前进一个窗口步骤，说明文字留给界面。"""
    from core.modules.strategy.core.services.progress import ROLLING_PIPELINE
    from core.infra.progress import Progress

    PipelineProgress.seed("demo/x", "job-roll", pipeline_name=ROLLING_PIPELINE)
    with PipelineProgress.bind("demo/x", "job-roll") as prog:
        prog.mark_running()
        prog.tick_execute(1, 6, description="20240101-20241231 枚举")
        assert prog.to_dict()["step"]["description"] == "20240101-20241231 枚举"
        assert prog.to_dict()["step"]["counters"] == {"done": 1, "total": 6}
        held = float(prog.to_dict()["step"]["progress"])
        prog.tick_execute(0, 3, description="下一窗")
        assert float(prog.to_dict()["step"]["progress"]) == held
        assert prog.to_dict()["step"]["counters"] == {"done": 0, "total": 3}

        shared = Progress.read("pipeline-demo-x-job-roll")
        assert shared["steps"][0]["done"] == 0
        assert shared["steps"][0]["total"] == 3
        assert PipelineProgress.drives_pipeline("enum") is False
        assert PipelineProgress.drives_pipeline(ROLLING_PIPELINE) is True
