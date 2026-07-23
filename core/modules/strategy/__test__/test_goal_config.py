#!/usr/bin/env python3
"""GoalSettings 解析单元测试。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)


class TestGoalSettings(unittest.TestCase):
    def test_parse_valid_goal(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {
                    "stop_loss": {
                        "stages": [
                            {"ratio": -0.2, "close_invest": True, "name": "loss20%"}
                        ]
                    },
                    "take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]},
                },
            }
        )
        goal = settings.goal
        self.assertIsNotNone(goal.stop_loss)
        self.assertIsNotNone(goal.take_profit)
        assert goal.stop_loss is not None
        assert goal.take_profit is not None
        self.assertEqual(goal.stop_loss.exit_ratio, 1.0)
        self.assertTrue(goal.stop_loss.close_invest)
        self.assertEqual(goal.take_profit.name, "win20%")
        self.assertEqual(goal.exit_price(goal.stop_loss, 10.0), 8.0)

    def test_rejects_missing_exit_spec(self) -> None:
        settings = StrategySettings(
            raw_settings={"goal": {"stop_loss": {"stages": [{"ratio": -0.2}]}}},
        )
        with self.assertRaises(ValueError):
            _ = settings.goal.stop_loss

    def test_partial_exit_ratio_from_sell_ratio(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {
                    "take_profit": {"stages": [{"ratio": 0.1, "sell_ratio": 0.5}]},
                },
            }
        )
        stage = settings.goal.take_profit
        assert stage is not None
        self.assertEqual(stage.exit_ratio, 0.5)
        self.assertFalse(stage.close_invest)
        self.assertEqual(stage.name, "win10%")

    def test_multi_stage_take_profit_with_actions(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {
                    "take_profit": {
                        "stages": [
                            {
                                "ratio": 0.1,
                                "exit_ratio": 0.5,
                                "actions": ["set_protect_loss"],
                            },
                            {
                                "ratio": 0.2,
                                "close_invest": True,
                                "actions": ["set_dynamic_loss"],
                            },
                        ]
                    },
                    "protect_loss": {"ratio": 0, "close_invest": True},
                    "dynamic_loss": {"ratio": -0.1, "close_invest": True},
                },
            }
        )
        stages = settings.goal.take_profit_stages
        self.assertEqual(len(stages), 2)
        self.assertEqual(stages[0].actions, ("set_protect_loss",))
        self.assertEqual(stages[1].actions, ("set_dynamic_loss",))
        protect = settings.goal.protect_loss
        dynamic = settings.goal.dynamic_loss
        assert protect is not None and dynamic is not None
        self.assertEqual(protect.ratio, 0.0)
        self.assertEqual(dynamic.ratio, -0.1)
        report = settings.validate()
        self.assertTrue(report.is_valid)

    def test_multi_stage_without_coverage_invalid(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {
                    "take_profit": {
                        "stages": [
                            {"ratio": 0.1, "exit_ratio": 0.3},
                            {"ratio": 0.2, "exit_ratio": 0.3},
                        ]
                    }
                },
            }
        )
        report = settings.validate()
        self.assertFalse(report.is_valid)

    def test_rejects_bad_action(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {
                    "take_profit": {
                        "stages": [
                            {
                                "ratio": 0.1,
                                "close_invest": True,
                                "actions": ["set_something_else"],
                            }
                        ]
                    }
                },
            }
        )
        with self.assertRaises(ValueError):
            _ = settings.goal.take_profit_stages

    def test_validate_reports_bad_stop_loss(self) -> None:
        settings = StrategySettings(
            raw_settings={"goal": {"stop_loss": {"stages": [{"ratio": -0.2}]}}},
        )
        report = settings.validate()
        self.assertFalse(report.is_valid)


if __name__ == "__main__":
    unittest.main()
