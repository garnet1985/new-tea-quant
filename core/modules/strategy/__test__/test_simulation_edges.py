"""SimulationSettings.edges：贴板成交政策（assumption.tradability.edges）。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.data_class.investments import (
    InvestmentRunDeps,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def _base_simulation(**tradability_overrides):
    tradability = {}
    tradability.update(tradability_overrides)
    return {
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
            "assumption": {"template": "none", "tradability": tradability},
            "risk_control": {},
        }
    }


def test_edges_default_deny_limit_fills() -> None:
    settings = StrategySettings.from_dict(_base_simulation())
    settings.apply_defaults()
    assert settings.simulation.allow_enter_at_limit_up is False
    assert settings.simulation.allow_exit_at_limit_down is False
    assert settings.simulation.edges.allow_enter_at_limit_up is False


def test_edges_can_allow_limit_fills() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(
            edges={
                "allow_enter_at_limit_up": True,
                "allow_exit_at_limit_down": True,
            }
        )
    )
    report = settings.validate()
    assert report.is_valid
    assert settings.simulation.allow_enter_at_limit_up is True
    assert settings.simulation.allow_exit_at_limit_down is True


def test_edges_invalid_type_critical() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(edges="bad")  # type: ignore[arg-type]
    )
    report = settings.validate()
    assert not report.is_valid
    assert any(
        "edges" in (e.get("field_path") or "") or "edges" in (e.get("message") or "")
        for e in report.errors
    )


def test_to_dict_includes_edges() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(edges={"allow_enter_at_limit_up": True})
    )
    dumped = settings.simulation.to_dict()
    edges = dumped["assumption"]["tradability"]["edges"]
    assert edges["allow_enter_at_limit_up"] is True
    assert edges["allow_exit_at_limit_down"] is False


def test_investment_run_deps_reads_edges() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(
            edges={
                "allow_enter_at_limit_up": True,
                "allow_exit_at_limit_down": False,
                "no_next_tick": "use_last_close",
            },
            slippage={"enter_bps": 5.0, "exit_bps": 3.0},
        )
    )
    settings.apply_defaults()
    deps = InvestmentRunDeps.from_settings(
        settings=settings,
        market_rules=object(),
        open_dates=["20240102", "20240103"],
    )
    assert deps.allow_enter_at_limit_up is True
    assert deps.allow_exit_at_limit_down is False
    assert deps.no_next_tick == "use_last_close"
    assert deps.slippage.enter_bps == 5.0
    assert deps.slippage.exit_bps == 3.0
