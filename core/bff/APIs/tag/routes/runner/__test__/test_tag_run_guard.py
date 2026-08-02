"""Tag runner guard tests (no full Tag run)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.bff.APIs.tag.routes.runner.tag_run import TagRunLauncher


def test_trigger_unknown_scenario():
    with patch.object(TagRunLauncher, "_find_info", return_value=None):
        out = TagRunLauncher.trigger(tag_key="no/such/tag")
    assert out["is_triggered"] is False
    assert "未知" in out["reason"]


def test_trigger_rejects_when_pipeline_busy(monkeypatch):
    monkeypatch.setattr(
        "core.infra.system_actions.system_actions.PipelineNamespace.read_status",
        lambda: {"busy": True, "kind": "strategy_run", "job_id": "x"},
    )
    info = MagicMock()
    info.id.return_value = "demo/x"
    info.settings = {"is_enabled": True}
    with patch.object(TagRunLauncher, "_find_info", return_value=info):
        out = TagRunLauncher.trigger(tag_key="demo/x")
    assert out["is_triggered"] is False
    assert "进行中" in out["reason"]
