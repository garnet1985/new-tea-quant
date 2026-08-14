"""simulation.assumption templates + nested settings shape。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    AssumptionTemplate,
    StrategySettings,
)


def _sim(**overrides):
    base = {
        "execution": {
            "mode": "entity_based",
        },
        "assumption": {"template": "none"},
        "risk_control": {},
    }
    base.update(overrides)
    return {"simulation": base}


def test_named_templates_resolve() -> None:
    for name in sorted(AssumptionTemplate.NAMED):
        cfg = AssumptionTemplate.tradability(name)
        assert cfg.enter_price
        assert cfg.edges
        assert cfg.liquidity


def test_standard_template_short_circuits_explicit_tradability() -> None:
    settings = StrategySettings.from_dict(
        _sim(
            assumption={
                "template": "standard",
                "tradability": {
                    "enter_price": "close",
                    "edges": {"allow_enter_at_limit_up": True},
                },
            }
        )
    )
    settings.apply_defaults()
    assert settings.simulation.enter_price == "touch"
    assert settings.simulation.allow_enter_at_limit_up is False
    assert settings.simulation.liquidity.participation_on_exceed == "clip"


def test_strict_vs_ideal() -> None:
    strict = StrategySettings.from_dict(_sim(assumption={"template": "strict"}))
    strict.apply_defaults()
    ideal = StrategySettings.from_dict(_sim(assumption={"template": "ideal"}))
    ideal.apply_defaults()
    assert strict.simulation.liquidity.participation_on_exceed == "skip"
    assert ideal.simulation.allow_enter_at_limit_up is True
    assert ideal.simulation.allow_exit_at_limit_down is True


def test_custom_uses_explicit_tradability() -> None:
    settings = StrategySettings.from_dict(
        _sim(
            assumption={
                "template": "custom",
                "tradability": {
                    "enter_price": "close",
                    "exit_price": "open",
                    "edges": {
                        "allow_enter_at_limit_up": True,
                        "allow_exit_at_limit_down": False,
                    },
                    "liquidity": {
                        "max_participation_rate": 0.2,
                        "participation_on_exceed": "skip",
                    },
                },
            }
        )
    )
    report = settings.validate()
    assert report.is_valid
    assert settings.simulation.enter_price == "close"
    assert settings.simulation.exit_price == "open"
    assert settings.simulation.allow_enter_at_limit_up is True
    assert settings.simulation.liquidity.max_participation_rate == 0.2


def test_risk_control_skip_and_force() -> None:
    settings = StrategySettings.from_dict(
        _sim(
            risk_control={
                "skip_enter_when": ["st"],
                "force_exit_when": ["star_st"],
            }
        )
    )
    report = settings.validate()
    assert report.is_valid
    assert settings.simulation.risk_control.skip_enter_when.tags == ("st",)
    assert settings.simulation.risk_control.force_exit_when.tags == ("star_st",)
    dumped = settings.simulation.to_dict()
    assert dumped["risk_control"]["skip_enter_when"] == ["st"]
    assert dumped["risk_control"]["force_exit_when"] == ["star_st"]


def test_canonical_template() -> None:
    assert AssumptionTemplate.canonicalize(None) == "none"
    assert AssumptionTemplate.canonicalize("") == "none"
    assert AssumptionTemplate.canonicalize("STANDARD") == "standard"
    with pytest.raises(ValueError):
        AssumptionTemplate.canonicalize("weird")
