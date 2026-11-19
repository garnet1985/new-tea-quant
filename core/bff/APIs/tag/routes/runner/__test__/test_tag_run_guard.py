"""Tag runner guard tests (no full Tag run)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.bff.APIs.tag.routes.runner.tag_run import TagRunLauncher as BffTagRunLauncher
from core.modules.tag.core.services.run_launcher import TagRunLauncher


def test_bff_delegates_to_tag_facade():
    with patch("core.modules.tag.Tag.trigger_run", return_value={"is_triggered": True}) as trig:
        out = BffTagRunLauncher.trigger(tag_key="demo/x")
    assert out["is_triggered"] is True
    trig.assert_called_once_with(tag_key="demo/x")


def test_trigger_unknown_scenario():
    with patch.object(TagRunLauncher, "_find_info", return_value=None):
        out = TagRunLauncher.trigger(tag_key="no/such/tag")
    assert out["is_triggered"] is False
    assert "未知" in out["reason"]


def test_trigger_queues_when_task_busy():
    info = MagicMock()
    info.id.return_value = "demo/x"
    info.settings = {"is_enabled": True}
    with patch.object(TagRunLauncher, "_find_info", return_value=info):
        with patch(
            "core.infra.job_pipeline.JobPipeline.has_running_job",
            return_value=True,
        ):
            with patch(
                "core.infra.job_pipeline.JobPipeline.enqueue",
                return_value={
                    "queued": True,
                    "is_triggered": False,
                    "job_id": "jp-pend-1",
                    "reason": "已加入管道队列，当前任务结束后将自动执行",
                },
            ) as enqueue:
                out = TagRunLauncher.trigger(tag_key="demo/x")
    assert out.get("queued") is True
    assert out.get("is_triggered") is False
    enqueue.assert_called_once()


def test_start_now_does_not_enqueue_when_local_busy():
    info = MagicMock()
    info.id.return_value = "demo/x"
    info.settings = {"is_enabled": True}
    with patch.object(TagRunLauncher, "_find_info", return_value=info):
        with patch.object(
            TagRunLauncher,
            "_has_active_tag_run_locked",
            return_value=True,
        ):
            with patch(
                "core.infra.job_pipeline.JobPipeline.enqueue"
            ) as enqueue:
                out = TagRunLauncher.start_now(tag_key="demo/x")
    assert out["is_triggered"] is False
    assert "运行中" in out["reason"]
    enqueue.assert_not_called()


def test_require_successful_run_rejects_unsaved_values():
    TagRunLauncher._require_successful_run(
        {"success": True, "tag_values_count": 3, "saved_tag_values": 3}
    )
    try:
        TagRunLauncher._require_successful_run(
            {"success": True, "tag_values_count": 3, "saved_tag_values": 0}
        )
    except RuntimeError as exc:
        assert "未全部落库" in str(exc)
    else:
        raise AssertionError("expected unsaved values to fail")

    try:
        TagRunLauncher._require_successful_run({"success": False, "fail": 2})
    except RuntimeError as exc:
        assert "2" in str(exc)
    else:
        raise AssertionError("expected failed run to raise")

    try:
        TagRunLauncher._require_successful_run(None)
    except RuntimeError as exc:
        assert "未完成" in str(exc)
    else:
        raise AssertionError("expected empty result to fail")
