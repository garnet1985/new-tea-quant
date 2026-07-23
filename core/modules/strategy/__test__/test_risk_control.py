"""RiskControl — settings section + skip_enter / force_exit API。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    RiskControl,
    StrategySettings,
)


def _settings(**risk_overrides) -> StrategySettings:
    return StrategySettings.from_dict(
        {
            "simulation": {
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
                "risk_control": dict(risk_overrides),
            }
        }
    )


def test_from_settings_skip_enter() -> None:
    settings = _settings(skip_enter_when=["st", "star_st"])
    settings.apply_defaults()
    risk = settings.simulation.risk_control
    assert risk.skip_enter_when.tags == ("st", "star_st")
    assert risk.should_skip_enter(status_tags=["st"]) == "stock_status:st"
    assert risk.should_skip_enter(status_tags=[]) is None


def test_with_skip_enter_helper() -> None:
    risk = RiskControl.with_skip_enter(["st"])
    assert risk.should_skip_enter(status_tags=["st"]) == "stock_status:st"


def test_should_force_exit_on_status_tag() -> None:
    settings = _settings(force_exit_when=["st"])
    settings.apply_defaults()
    risk = settings.simulation.risk_control
    decision = risk.should_force_exit(
        entity_id="600000.SH",
        trade_date="20240102",
        status_tags=["st"],
    )
    assert decision is not None
    assert decision.reason == "stock_status:st"
    assert decision.close_invest is True
    assert decision.exit_ratio == 1.0
    assert (
        risk.should_force_exit(
            entity_id="600000.SH",
            trade_date="20240102",
            status_tags=["st"],
            already_triggered=["st"],
        )
        is None
    )


def test_force_exit_when_rule_object_partial() -> None:
    settings = _settings(
        force_exit_when=[
            {"status": "st", "close_invest": False, "exit_ratio": 0.5},
        ]
    )
    settings.apply_defaults()
    risk = settings.simulation.risk_control
    rule = risk.force_exit_when.rules[0]
    assert rule.status == "st"
    assert rule.close_invest is False
    assert rule.exit_ratio == 0.5
    decision = risk.should_force_exit(
        entity_id="600000.SH",
        trade_date="20240102",
        status_tags=["st"],
    )
    assert decision is not None
    assert decision.close_invest is False
    assert decision.exit_ratio == 0.5
    dumped = settings.simulation.to_dict()["risk_control"]["force_exit_when"]
    assert dumped == [
        {"status": "st", "close_invest": False, "exit_ratio": 0.5}
    ]


def test_force_exit_when_rule_close_invest() -> None:
    settings = _settings(
        force_exit_when=[{"status": "star_st", "close_invest": True}]
    )
    settings.apply_defaults()
    risk = settings.simulation.risk_control
    decision = risk.should_force_exit(
        entity_id="600000.SH",
        trade_date="20240102",
        status_tags=["star_st"],
    )
    assert decision is not None
    assert decision.close_invest is True
    assert decision.exit_ratio == 1.0


def test_should_force_exit_delisted() -> None:
    risk = RiskControl(raw_settings={"simulation": {"risk_control": {}}})
    decision = risk.should_force_exit(
        entity_id="600000.SH",
        trade_date="20240601",
        stock_meta={"delist_date": "20240501"},
    )
    assert decision is not None
    assert decision.reason == "stock_status:delisted"
