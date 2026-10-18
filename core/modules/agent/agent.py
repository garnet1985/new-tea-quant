"""Agent 门面 — 列出已登记工具。运行循环尚未对外暴露。"""

from __future__ import annotations

from typing import List

from core.modules.agent.contracts import ToolSpec
from core.modules.agent.core.agent_manager import AgentManager


class Agent:
    """AI agent 门面。"""

    _manager = AgentManager()

    @staticmethod
    def list_tools() -> List[ToolSpec]:
        """返回已登记的工具说明。``implemented`` 为假表示还不能执行。"""
        return Agent._manager.list_tools()


__all__ = ["Agent"]
