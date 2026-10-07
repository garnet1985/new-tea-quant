"""归因接口测试：按钮状态、启动和报告。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.bff.APIs.strategy.routes.attribution.attribute_run import AttributeRunLauncher
from core.bff.APIs.strategy.routes.attribution.report import AttributeReportReader
from core.bff.APIs.strategy.routes.attribution.status import AttributeStatus, EXAMPLE_PATH
from core.modules.strategy.core.engines.analyzer.steps.campaign.persist.base import (
    REPORT_FILE,
)

pytestmark = pytest.mark.force_run


def test_normalize_step():
    assert AttributeRunLauncher.normalize_step("enum") == "enum"
    assert AttributeRunLauncher.normalize_step("PRICE") == "price"
    assert AttributeRunLauncher.normalize_step("nope") is None


def test_status_hidden_without_primary(tmp_path, monkeypatch):
    folder = tmp_path / "strat"
    folder.mkdir()
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.attribution.status.Strategy.resolve_folder",
        staticmethod(lambda key: folder),
    )
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.attribution.status.DiscoveryService.find_strategy",
        staticmethod(lambda key: MagicMock()),
    )
    monkeypatch.setattr(
        AttributeStatus,
        "_has_primary",
        classmethod(lambda cls, folder, name, kind: (False, None)),
    )
    out = AttributeStatus.probe("demo/x", "enum")
    assert out["visible"] is False
    assert out["enabled"] is False
    assert out["reason"] == "layer_not_run"
    assert "完成本层回测" in out["tooltip"]
    assert "attribution.py" in out["tooltip"]
    assert EXAMPLE_PATH in out["example_path"]


def test_status_disabled_without_attribution_file(tmp_path, monkeypatch):
    folder = tmp_path / "strat"
    folder.mkdir()
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.attribution.status.Strategy.resolve_folder",
        staticmethod(lambda key: folder),
    )
    monkeypatch.setattr(
        AttributeStatus,
        "_has_primary",
        classmethod(lambda cls, folder, name, kind: (True, "21")),
    )
    monkeypatch.setattr(
        AttributeStatus,
        "_last_group_id",
        classmethod(lambda cls, folder, name, step, primary_vid=None: None),
    )
    out = AttributeStatus.probe("demo/x", "enum")
    assert out["visible"] is True
    assert out["enabled"] is False
    assert out["reason"] == "attribution_not_configured"
    assert "attribution.py" in out["tooltip"]


def test_status_enabled_with_overlays(tmp_path, monkeypatch):
    folder = tmp_path / "strat"
    folder.mkdir()
    (folder / "attribution.py").write_text(
        "attribution = {'price_factor': {'inputs': {"
        "'opportunity_merge_gap': {'values': [1, 3]}}}}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.attribution.status.Strategy.resolve_folder",
        staticmethod(lambda key: folder),
    )
    monkeypatch.setattr(
        AttributeStatus,
        "_has_primary",
        classmethod(lambda cls, folder, name, kind: (True, "21")),
    )
    monkeypatch.setattr(
        AttributeStatus,
        "_last_group_id",
        classmethod(lambda cls, folder, name, step, primary_vid=None: "3"),
    )
    out = AttributeStatus.probe("demo/x", "price")
    assert out["visible"] is True
    assert out["enabled"] is True
    assert out["reason"] == "ok"
    assert out["last_group_id"] == "3"
    assert out["config_ok"] is True


def test_status_invalid_when_only_rolling(tmp_path, monkeypatch):
    folder = tmp_path / "strat"
    folder.mkdir()
    (folder / "attribution.py").write_text(
        "attribution = {'rolling': {'windows': [{'start': '20230101', 'end': '20231231'}]}}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.attribution.status.Strategy.resolve_folder",
        staticmethod(lambda key: folder),
    )
    monkeypatch.setattr(
        AttributeStatus,
        "_has_primary",
        classmethod(lambda cls, folder, name, kind: (True, "21")),
    )
    monkeypatch.setattr(
        AttributeStatus,
        "_last_group_id",
        classmethod(lambda cls, folder, name, step, primary_vid=None: None),
    )
    out = AttributeStatus.probe("demo/x", "portfolio")
    assert out["visible"] is True
    assert out["enabled"] is False
    assert out["reason"] == "attribution_invalid"


def test_report_reader_loads_artifacts(tmp_path, monkeypatch):
    folder = tmp_path / "strat"
    task_dir = tmp_path / "attr" / "3" / "enumerate"
    task_dir.mkdir(parents=True)
    (task_dir / REPORT_FILE).write_text(
        json.dumps({"headline": "hello", "trades": {}}),
        encoding="utf-8",
    )
    (task_dir / "table.json").write_text("[]", encoding="utf-8")
    (task_dir / "attribute.json").write_text("{}", encoding="utf-8")
    (task_dir / "task_meta.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.attribution.report.Strategy.resolve_folder",
        staticmethod(lambda key: folder),
    )
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.attribution.report.ProjectContext.path.get_strategy_attribution_directory",
        lambda f: tmp_path / "attr",
    )
    msg = AttributeReportReader.build(
        strategy_name="demo/x",
        normalized_step="enum",
        group_id="3",
    )
    assert msg["headline"] == "hello"
    assert msg["group_id"] == "3"
    assert msg["layer"] == "enumerate"
    assert msg["step"] == "enum"


@patch(
    "core.infra.task_guard.task_guard.TaskGuard.read_status",
    return_value={"busy": False},
)
@patch(
    "core.bff.APIs.strategy.routes.attribution.attribute_run.DiscoveryService.find_strategy",
    return_value=MagicMock(),
)
def test_submit_gated_when_status_disabled(_find, _busy):
    with patch.object(
        AttributeRunLauncher,
        "_gate",
        return_value="需要配置 attribution.py 才能做归因。",
    ):
        out = AttributeRunLauncher.submit(
            strategy_name="demo/x",
            step="enum",
            force_refresh=False,
        )
    assert out["is_triggered"] is False
    assert "attribution" in out["reason"]
