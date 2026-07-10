#!/usr/bin/env python3
"""GoalSettings 解析单元测试。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.engines.shared.services.strategy_settings import StrategySettings


class TestGoalSettings(unittest.TestCase):
    def test_parse_valid_goal(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {
                    "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True, "name": "loss20%"}]},
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

    def test_validate_reports_bad_stop_loss(self) -> None:
        settings = StrategySettings(
            raw_settings={"goal": {"stop_loss": {"stages": [{"ratio": -0.2}]}}},
        )
        report = settings.validate()
        self.assertFalse(report.is_valid)


if __name__ == "__main__":
    unittest.main()
