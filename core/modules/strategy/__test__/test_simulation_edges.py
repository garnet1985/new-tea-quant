"""SimulationSettings.edges：贴板成交政策。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.data_class.investment import (
    InvestmentRunDeps,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def _base_simulation(**overrides):
    sim = {
        "execute_steps": [
            "check_settlement",
            "check_stop_loss",
            "check_take_profit",
            "check_expiration",
        ],
    }
    sim.update(overrides)
    return {"simulation": sim}


def test_edges_default_deny_limit_fills() -> None:
    settings = StrategySettings.from_dict(_base_simulation())
    settings.apply_defaults()
    assert settings.simulation.allow_buy_at_limit_up is False
    assert settings.simulation.allow_sell_at_limit_down is False
    assert settings.simulation.edges.allow_buy_at_limit_up is False


def test_edges_can_allow_limit_fills() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(
            edges={
                "allow_buy_at_limit_up": True,
                "allow_sell_at_limit_down": True,
            }
        )
    )
    report = settings.validate()
    assert report.is_valid
    assert settings.simulation.allow_buy_at_limit_up is True
    assert settings.simulation.allow_sell_at_limit_down is True


def test_edges_invalid_type_critical() -> None:
    settings = StrategySettings.from_dict(_base_simulation(edges="bad"))
    report = settings.validate()
    assert not report.is_valid
    assert any("edges" in (e.get("field_path") or "") for e in report.errors)


def test_to_dict_includes_edges() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(edges={"allow_buy_at_limit_up": True})
    )
    dumped = settings.simulation.to_dict()
    assert dumped["edges"]["allow_buy_at_limit_up"] is True
    assert dumped["edges"]["allow_sell_at_limit_down"] is False


def test_investment_run_deps_reads_edges() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(
            edges={
                "allow_buy_at_limit_up": True,
                "allow_sell_at_limit_down": False,
            }
        )
    )
    settings.apply_defaults()
    deps = InvestmentRunDeps.from_settings(
        settings=settings,
        market_rules=object(),
        open_dates=["20240102", "20240103"],
    )
    assert deps.allow_buy_at_limit_up is True
    assert deps.allow_sell_at_limit_down is False
