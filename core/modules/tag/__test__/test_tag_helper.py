"""TagHelper 单元测试。"""
from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.modules.tag.base_tag_worker import BaseTagWorker
from core.modules.tag.components.helper.tag_helper import TagHelper


class _TestWorker(BaseTagWorker):
    def calculate_tag(self, data, as_of_date):
        return {"value": 1}


def test_load_scenario_settings_success():
    mock_settings_path = Path("/test/scenario/settings.py")
    with patch(
        "core.modules.tag.components.helper.tag_helper.FileManager.find_file"
    ) as mock_find_file, patch(
        "core.modules.tag.components.helper.tag_helper.ConfigManager.load_python"
    ) as mock_load_python:
        mock_find_file.return_value = mock_settings_path
        mock_load_python.return_value = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {
                "required": [
                    {
                        "data_id": "stock.kline",
                        "params": {"term": "daily", "adjust": "qfq"},
                    }
                ]
            },
            "tags": [{"name": "tag1"}],
        }

        settings_path, settings_dict = TagHelper.load_scenario_settings(
            Path("/test/scenario")
        )

    assert settings_path == mock_settings_path
    assert settings_dict is not None
    assert settings_dict["name"] == "test_scenario"
    mock_load_python.assert_called_once_with(mock_settings_path, var_name="Settings")


@pytest.mark.parametrize(
    "find_return,load_return",
    [
        (None, None),
        (Path("/test/scenario/settings.py"), None),
        (Path("/test/scenario/settings.py"), "not a dict"),
    ],
)
def test_load_scenario_settings_failure(find_return, load_return):
    with patch(
        "core.modules.tag.components.helper.tag_helper.FileManager.find_file"
    ) as mock_find_file, patch(
        "core.modules.tag.components.helper.tag_helper.ConfigManager.load_python"
    ) as mock_load_python:
        mock_find_file.return_value = find_return
        mock_load_python.return_value = load_return

        settings_path, settings_dict = TagHelper.load_scenario_settings(
            Path("/test/scenario")
        )

    assert settings_path is None
    assert settings_dict is None


def test_load_worker_class_success():
    mock_worker_path = Path("/test/scenario/tag_worker.py")
    with patch(
        "core.modules.tag.components.helper.tag_helper.FileManager.find_file"
    ) as mock_find_file, patch(
        "importlib.util.spec_from_file_location"
    ) as mock_spec_from_file, patch(
        "importlib.util.module_from_spec"
    ) as mock_module_from_spec:
        mock_find_file.return_value = mock_worker_path
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec
        mock_module = types.ModuleType("tag_worker")
        mock_module.TestWorker = _TestWorker
        mock_module.BaseTagWorker = BaseTagWorker
        mock_module_from_spec.return_value = mock_module

        worker_path, worker_class = TagHelper.load_worker_class(Path("/test/scenario"))

    assert worker_path == mock_worker_path
    assert worker_class is _TestWorker


def test_load_worker_class_file_not_found():
    with patch(
        "core.modules.tag.components.helper.tag_helper.FileManager.find_file",
        return_value=None,
    ):
        worker_path, worker_class = TagHelper.load_worker_class(Path("/test/scenario"))

    assert worker_path is None
    assert worker_class is None


def test_load_worker_class_no_worker_class():
    mock_worker_path = Path("/test/scenario/tag_worker.py")
    with patch(
        "core.modules.tag.components.helper.tag_helper.FileManager.find_file",
        return_value=mock_worker_path,
    ), patch("importlib.util.spec_from_file_location") as mock_spec_from_file, patch(
        "importlib.util.module_from_spec"
    ) as mock_module_from_spec:
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec
        mock_module = types.ModuleType("tag_worker")
        mock_module.SomeOtherClass = object
        mock_module_from_spec.return_value = mock_module

        worker_path, worker_class = TagHelper.load_worker_class(Path("/test/scenario"))

    assert worker_path is None
    assert worker_class is None


@pytest.mark.parametrize(
    "spec",
    [None, MagicMock(loader=None)],
    ids=["spec_none", "loader_none"],
)
def test_load_worker_class_invalid_spec(spec):
    mock_worker_path = Path("/test/scenario/tag_worker.py")
    with patch(
        "core.modules.tag.components.helper.tag_helper.FileManager.find_file",
        return_value=mock_worker_path,
    ), patch(
        "importlib.util.spec_from_file_location",
        return_value=spec,
    ):
        worker_path, worker_class = TagHelper.load_worker_class(Path("/test/scenario"))

    assert worker_path is None
    assert worker_class is None
