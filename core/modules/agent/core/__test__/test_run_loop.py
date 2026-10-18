"""运行循环在接通模型前只说明自己还不能跑。"""

from __future__ import annotations

import unittest

import pytest

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.run_loop import RunLoop

pytestmark = pytest.mark.force_run


class TestRunLoop(unittest.TestCase):
    def test_run_loop_is_not_connected(self) -> None:
        loop = RunLoop()
        with self.assertRaises(AgentError) as blank:
            loop.run("  ")
        self.assertIn("空", str(blank.exception))

        with self.assertRaises(AgentError) as pending:
            loop.run("写一个 MACD 策略")
        self.assertIn("尚未接通", str(pending.exception))
