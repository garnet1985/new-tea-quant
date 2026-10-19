"""Agent implementer — 懒加载 ``modules.agent``。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _status_for_agent_error(exc: Exception) -> int:
    msg = str(exc)
    if "用完" in msg or "额度" in msg or "猫粮" in msg:
        return 429
    if "凭证" in msg:
        return 401
    if any(
        token in msg
        for token in ("空", "未找到", "没有可用", "未配置", "已禁用", "过长", "上限")
    ):
        return 400
    return 502


class AgentImplementer:
    def __init__(self) -> None:
        self._Agent = None
        self._AgentError = None

    def lazy_load(self) -> "AgentImplementer":
        if self._Agent is None:
            from core.modules.agent import Agent
            from core.modules.agent.contracts import AgentError

            self._Agent = Agent
            self._AgentError = AgentError
        return self

    def run(
        self,
        content: str,
        session_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Agent is not None
        assert self._AgentError is not None
        text = str(content or "").strip()
        if not text:
            return None, "消息不能为空", 400
        sid = str(session_id or "").strip() or None
        try:
            reply = self._Agent.run(text, session_id=sid)
        except self._AgentError as exc:
            return None, str(exc), _status_for_agent_error(exc)
        except Exception as exc:  # noqa: BLE001 — surface unexpected failures to the dock
            return None, str(exc) or "Agent 执行失败", 502
        return {
            "reply": str(reply or ""),
            "sessionId": sid or "default",
        }, None, 200

    def clear_session(
        self,
        session_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Agent is not None
        assert self._AgentError is not None
        sid = str(session_id or "").strip() or None
        try:
            self._Agent.clear_session(sid)
        except self._AgentError as exc:
            return None, str(exc), _status_for_agent_error(exc)
        return {"cleared": True, "sessionId": sid or "default"}, None, 200


impl = AgentImplementer()
