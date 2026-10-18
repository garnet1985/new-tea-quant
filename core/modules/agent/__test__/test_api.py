"""API contract tests for modules.agent Facade."""

from __future__ import annotations

import unittest

import pytest

from core.modules.agent import Agent
from core.modules.agent.contracts import ToolSpec

pytestmark = pytest.mark.force_run

_TOOL_NAMES = (
    "create_strategy",
    "write_strategy_files",
    "validate_strategy",
    "start_simulate",
    "read_progress",
    "read_report",
)


class TestAgentApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.agent as pkg

        self.assertEqual(pkg.__all__, ["Agent"])
        self.assertFalse(hasattr(pkg, "ToolSpec"))
        self.assertFalse(hasattr(pkg, "AgentError"))
        self.assertFalse(hasattr(pkg, "AgentManager"))
        self.assertFalse(hasattr(pkg, "RunLoop"))
        self.assertFalse(hasattr(pkg, "list_tools"))

    def test_list_tools_are_registered_but_not_implemented(self) -> None:
        tools = Agent.list_tools()
        self.assertEqual(tuple(tool.name for tool in tools), _TOOL_NAMES)
        self.assertTrue(all(tool.implemented is False for tool in tools))

    def test_tool_spec_fields(self) -> None:
        fields = set(ToolSpec.__dataclass_fields__)
        self.assertEqual(fields, {"name", "description", "parameters", "implemented"})
        self.assertNotIn("api_key", fields)
        self.assertNotIn("handler", fields)
