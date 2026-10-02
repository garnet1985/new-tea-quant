"""PriceReplaySettings：opportunity_merge_gap 默认 / 校验。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def test_opportunity_merge_gap_defaults_to_one() -> None:
    settings = StrategySettings.from_dict({"simulation": {"execution": {"mode": "entity_based"}}})
    settings.apply_defaults()
    assert settings.simulation.price.opportunity_merge_gap == 1
    dumped = settings.simulation.to_dict()
    assert dumped["price"]["opportunity_merge_gap"] == 1


def test_opportunity_merge_gap_zero_allowed() -> None:
    settings = StrategySettings.from_dict(
        {
            "simulation": {
                "execution": {"mode": "entity_based"},
                "price": {"opportunity_merge_gap": 0},
            }
        }
    )
    report = settings.validate()
    assert report.is_valid
    assert settings.simulation.price.opportunity_merge_gap == 0


def test_opportunity_merge_gap_rejects_negative() -> None:
    settings = StrategySettings.from_dict(
        {
            "simulation": {
                "execution": {"mode": "entity_based"},
                "price": {"opportunity_merge_gap": -1},
            }
        }
    )
    report = settings.validate()
    assert not report.is_valid


def test_opportunity_merge_gap_rejects_bool() -> None:
    settings = StrategySettings.from_dict(
        {
            "simulation": {
                "execution": {"mode": "entity_based"},
                "price": {"opportunity_merge_gap": True},
            }
        }
    )
    report = settings.validate()
    assert not report.is_valid
