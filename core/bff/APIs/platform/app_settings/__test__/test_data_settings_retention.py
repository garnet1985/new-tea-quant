"""data.json settings: simulation keep-N field."""

from __future__ import annotations

import pytest

from core.bff.APIs.platform.app_settings.service import (
    data_settings_response,
    normalize_positive_int,
)

pytestmark = pytest.mark.force_run


def test_normalize_positive_int():
    assert normalize_positive_int("10", "simulation_results_max_versions") == 10
    with pytest.raises(ValueError, match="大于 0"):
        normalize_positive_int("0", "simulation_results_max_versions")
    with pytest.raises(ValueError, match="正整数"):
        normalize_positive_int(None, "simulation_results_max_versions")


def test_data_settings_response_includes_retention(monkeypatch):
    class _Cfg:
        @staticmethod
        def get_simulation_results_max_versions():
            return 10

    class _Path:
        @staticmethod
        def get_user_config_root():
            from pathlib import Path

            return Path("/tmp/userspace/config")

    monkeypatch.setattr(
        "core.bff.APIs.platform.app_settings.service._get_as_of_latest_completed_trading_date",
        lambda: None,
    )
    monkeypatch.setattr(
        "core.bff.APIs.platform.app_settings.service.ProjectContext.config",
        _Cfg,
    )
    monkeypatch.setattr(
        "core.bff.APIs.platform.app_settings.service.ProjectContext.path",
        _Path,
    )
    out = data_settings_response(
        {"default_start_date": "20080101", "use_sample_stock_list": None}
    )
    assert out["simulation_results_max_versions"] == 10
    assert out["default_start_date"] == "20080101"
