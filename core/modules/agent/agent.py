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
    def run(content: str, *, session_id: Optional[str] = None) -> str:
        """先用免费模型判断回答还是做事；做事交给 deepseek-flash，并写入会话记录。"""
        return Agent._manager.run(content, session_id=session_id)

    @staticmethod
    def clear_session(session_id: Optional[str] = None) -> None:
        """清空会话对话与局部状态。不清除跨会话偏好。"""
        Agent._manager.clear_session(session_id)

    @staticmethod
    def list_preferences() -> List[str]:
        """返回跨会话偏好列表。"""
        return Agent._manager.list_preferences()

    @staticmethod
    def remember(rule: str) -> List[str]:
        """追加一条跨会话偏好。"""
        return Agent._manager.remember(rule)

    @staticmethod
    def forget(rule: str) -> List[str]:
        """删除一条跨会话偏好。"""
        return Agent._manager.forget(rule)


__all__ = ["Agent"]
