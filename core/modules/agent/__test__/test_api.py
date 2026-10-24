"""公开 Facade 冒烟。"""

from __future__ import annotations

import pytest

import core.modules.agent as pkg
from core.modules.agent import Agent
from core.modules.agent.contracts import AgentError, ToolSpec

pytestmark = pytest.mark.force_run


def test_facade_exports() -> None:
    assert pkg.__all__ == ["Agent"]
    for name in (
        "list_tools",
        "call_tool",
        "run",
        "clear_session",
        "session_history",
        "list_preferences",
        "remember",
        "forget",
        "get_settings",
        "update_settings",
    ):
        assert callable(getattr(Agent, name)), name


def test_tool_specs_are_unique_and_typed() -> None:
    tools = Agent.list_tools()
    assert tools
    assert all(isinstance(item, ToolSpec) for item in tools)
    names = [item.name for item in tools]
    assert len(names) == len(set(names))
    assert all(isinstance(item.implemented, bool) for item in tools)


def test_unknown_tool_raises() -> None:
    with pytest.raises(AgentError):
        Agent.call_tool("__no_such_tool__", {})
