"""SimulationSettings：execution.start/end date 校验。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings import StrategySettings

pytestmark = pytest.mark.force_run


def _base_simulation(**overrides):
    sim = {
        "execution": {
            "mode": "entity_based",
            "steps": [
                "check_settlement",
                "check_stop_loss",
                "check_take_profit",
                "check_expiration",
            ],
        },
        "assumption": {"template": "none"},
        "risk_control": {},
    }
    execution = sim["execution"]
    for key in ("start_date", "end_date", "mode", "steps"):
        if key in overrides:
            execution[key] = overrides.pop(key)
    sim.update(overrides)
    return {"simulation": sim}


def test_simulation_period_valid() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(start_date="20240101", end_date="20240630")
    )
    report = settings.validate()
    assert report.is_valid
    assert settings.is_valid()
    assert settings.simulation.start_date == "20240101"
    assert settings.simulation.end_date == "20240630"
    assert settings.start_date == "20240101"
    assert settings.end_date == "20240630"


def test_simulation_period_empty_ok() -> None:
    settings = StrategySettings.from_dict(_base_simulation())
    report = settings.validate()
    assert report.is_valid
    assert settings.start_date == ""
    assert settings.end_date == ""


def test_simulation_period_invalid_format() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(start_date="2024-01-01", end_date="20240630")
    )
    report = settings.validate()
    assert not report.is_valid
    assert not settings.is_valid()
    assert any("start_date" in (e.get("field_path") or "") for e in report.errors)


def test_simulation_period_start_after_end() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(start_date="20241231", end_date="20240101")
    )
    report = settings.validate()
    assert not report.is_valid


def test_legacy_sampling_dates_warn_only() -> None:
    raw = _base_simulation(start_date="20240101", end_date="20240630")
    raw["sampling"] = {"use_sampling": False, "start_date": "20100101", "end_date": "20101231"}
    settings = StrategySettings.from_dict(raw)
    report = settings.validate()
    assert report.is_valid
    assert any("sampling" in (w.get("field_path") or "") for w in report.warnings)
    assert settings.start_date == "20240101"
