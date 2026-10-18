"""Agent 门面 — 列出工具，并执行已实现的调用单。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.agent.contracts import ToolSpec
from core.modules.agent.core.agent_manager import AgentManager


class Agent:
    """AI agent 门面。"""

    _manager = AgentManager()

    @staticmethod
    def list_tools() -> List[ToolSpec]:
        """返回已登记的工具说明。``implemented`` 为假表示还不能执行。"""
        return Agent._manager.list_tools()

    @staticmethod
    def call_tool(
        name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行一张调用单。未知工具或尚未实现时抛 AgentError。"""
        return Agent._manager.call_tool(name, arguments)

    @staticmethod
    def run(content: str) -> str:
        """把一句话交给会员通道上的 glm-4-flash，按它的调用单执行工具，直到它写出给人看的话。"""
        return Agent._manager.run(content)


__all__ = ["Agent"]
