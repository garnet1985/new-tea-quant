"""Tag launcher guard tests (no full TagManager run)."""

from __future__ import annotations

from unittest.mock import patch

from core.modules.tag.launcher import tag_run


def test_trigger_unknown_scenario():
    out = tag_run.trigger_tag_run(tag_key="no/such/tag")
    assert out["is_triggered"] is False
    assert "未知" in out["reason"]


def test_trigger_rejects_when_pipeline_busy(monkeypatch):
    monkeypatch.setattr(
        tag_run,
        "read_pipeline_status",
        lambda: {"busy": True, "kind": "strategy_run", "job_id": "x"},
    )
    with patch.object(tag_run.TagDiscoveryHelper, "discover_tags") as mock_disc:
        mock_disc.return_value = {
            "demo/x": type(
                "Item",
                (),
                {"tag_key": "demo/x", "settings": {"is_enabled": True}},
            )()
        }
        out = tag_run.trigger_tag_run(tag_key="demo/x")
    assert out["is_triggered"] is False
    assert "进行中" in out["reason"]
