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
    def run(
        content: str,
        *,
        session_id: Optional[str] = None,
        provider_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """锁定 Provider → Navigator → 流向。默认 ``ntq``；或传某一个自备 ``provider_id``。

        返回 ``reply`` / ``mode`` / ``catfood_spent`` / ``balance`` 等，供 UI 展示。
        """
        return Agent._manager.run(
            content, session_id=session_id, provider_id=provider_id
        )

    @staticmethod
    def clear_session(session_id: Optional[str] = None) -> None:
        """清空会话对话与局部状态。不清除跨会话偏好。"""
        Agent._manager.clear_session(session_id)

    @staticmethod
    def session_history(
        session_id: Optional[str] = None, *, limit: int = 20
    ) -> Dict[str, Any]:
        """返回本机会话最近若干轮人话，供 UI 刷新后恢复展示。"""
        return Agent._manager.session_history(session_id, limit=limit)

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
