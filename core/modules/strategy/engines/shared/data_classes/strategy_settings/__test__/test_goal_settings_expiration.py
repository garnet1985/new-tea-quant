#!/usr/bin/env python3
"""StrategyGoalSettings：expiration 可选。"""

from core.modules.strategy.engines.shared.data_classes.strategy_settings.goal_settings import (
    StrategyGoalSettings,
)


def test_missing_expiration_is_valid_without_warning():
    goal = {
        "stop_loss": {"stages": [{"name": "loss20%", "ratio": -0.2, "close_invest": True}]},
        "take_profit": {"stages": [{"name": "win20%", "ratio": 0.2, "close_invest": True}]},
    }
    report = StrategyGoalSettings.validate_goal_dict(goal, "demo", "goal")
    assert report.is_valid
    assert not any("expiration" in (w.message or "").lower() for w in report.warnings)


def test_apply_defaults_does_not_create_expiration():
    inst = StrategyGoalSettings.from_strategy_root(
        {
            "goal": {
                "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
                "take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]},
            }
        }
    )
    inst.apply_defaults()
    assert "expiration" not in inst.goal
