#!/usr/bin/env python3
"""GoalConfig 严格解析单元测试。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.helpers.goal_config import GoalConfig


class TestGoalConfig(unittest.TestCase):
    def test_parse_valid_goal(self) -> None:
        cfg = GoalConfig.from_settings(
            {
                "goal": {
                    "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True, "name": "loss20%"}]},
                    "take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]},
                },
            }
        )
        self.assertIsNotNone(cfg.stop_loss)
        self.assertIsNotNone(cfg.take_profit)
        self.assertEqual(cfg.exit_price(cfg.stop_loss, 10.0), 8.0)

    def test_rejects_missing_close_invest(self) -> None:
        with self.assertRaises(ValueError):
            GoalConfig.from_settings(
                {"goal": {"stop_loss": {"stages": [{"ratio": -0.2}]}}},
            )


if __name__ == "__main__":
    unittest.main()
