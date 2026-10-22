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

    def ntq_quota(self) -> Dict[str, Any]:
        """会员猫粮余额快照（产品 NTQ dock 用）。"""
        from core.modules.ntq_external.ai.member_channel import fetch_member_quota

        snap = fetch_member_quota()
        if not snap:
            return {
                "available": False,
                "limit": None,
                "remaining": None,
                "used": None,
                "balance": None,
                "token_balance": None,
                "currency": "猫粮",
            }
        return {"available": True, **snap}

    def run(
        self,
        content: str,
        session_id: Optional[str] = None,
        provider_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Agent is not None
        assert self._AgentError is not None
        text = str(content or "").strip()
        if not text:
            return None, "消息不能为空", 400
        sid = str(session_id or "").strip() or None
        pid = str(provider_id or "").strip() or None
        try:
            outcome = self._Agent.run(text, session_id=sid, provider_id=pid)
        except self._AgentError as exc:
            return None, str(exc), _status_for_agent_error(exc)
        except Exception as exc:  # noqa: BLE001 — surface unexpected failures to the dock
            return None, str(exc) or "Agent 执行失败", 502
        if isinstance(outcome, dict):
            reply = str(outcome.get("reply") or "")
            mode = str(outcome.get("mode") or ("work" if outcome.get("handoff") else "ask"))
            try:
                spent = round(max(0.0, float(outcome.get("catfood_spent") or 0)), 2)
            except (TypeError, ValueError):
                spent = 0.0
            balance = outcome.get("balance")
            try:
                balance_out = None if balance is None else round(max(0.0, float(balance)), 2)
            except (TypeError, ValueError):
                balance_out = None
        else:
            reply = str(outcome or "")
            mode = "ask"
            spent = 0.0
            balance_out = None
        return {
            "reply": reply,
            "sessionId": sid or "default",
            "mode": mode,
            "catfoodSpent": spent,
            "balance": balance_out,
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

    def session_history(
        self,
        session_id: Optional[str] = None,
        *,
        limit: int = 20,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Agent is not None
        assert self._AgentError is not None
        sid = str(session_id or "").strip() or None
        try:
            outcome = self._Agent.session_history(sid, limit=limit)
        except self._AgentError as exc:
            return None, str(exc), _status_for_agent_error(exc)
        except Exception as exc:  # noqa: BLE001
            return None, str(exc) or "读取会话失败", 502
        messages = outcome.get("messages") if isinstance(outcome, dict) else []
        if not isinstance(messages, list):
            messages = []
        return {
            "sessionId": str((outcome or {}).get("session_id") or sid or "default"),
            "messages": [
                {
                    "role": str(item.get("role") or ""),
                    "content": str(item.get("content") or ""),
                }
                for item in messages
                if isinstance(item, dict) and item.get("content")
            ],
        }, None, 200

    def get_settings(self) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Agent is not None
        assert self._AgentError is not None
        try:
            raw = self._Agent.get_settings()
        except self._AgentError as exc:
            return None, str(exc), _status_for_agent_error(exc)
        except Exception as exc:  # noqa: BLE001
            return None, str(exc) or "读取 Agent 设置失败", 502
        return self._settings_payload(raw), None, 200

    def update_settings(
        self, payload: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Agent is not None
        assert self._AgentError is not None
        kwargs: Dict[str, Any] = {}
        if "defaultProviderId" in payload or "default_provider_id" in payload:
            kwargs["default_provider_id"] = str(
                payload.get("defaultProviderId", payload.get("default_provider_id"))
                or ""
            ).strip()
        if "contextPrompt" in payload or "context_prompt" in payload:
            kwargs["context_prompt"] = str(
                payload.get("contextPrompt", payload.get("context_prompt")) or ""
            )
        if "preferences" in payload:
            rules = payload.get("preferences")
            if rules is None:
                kwargs["preferences"] = []
            elif isinstance(rules, list):
                kwargs["preferences"] = [str(item or "") for item in rules]
            else:
                return None, "preferences 须为字符串数组", 400
        if not kwargs:
            return None, "没有可更新的字段", 400
        try:
            raw = self._Agent.update_settings(**kwargs)
        except ValueError as exc:
            return None, str(exc), 400
        except self._AgentError as exc:
            return None, str(exc), _status_for_agent_error(exc)
        except Exception as exc:  # noqa: BLE001
            return None, str(exc) or "保存 Agent 设置失败", 502
        return self._settings_payload(raw), None, 200

    @staticmethod
    def _settings_payload(raw: Any) -> Dict[str, Any]:
        data = raw if isinstance(raw, dict) else {}
        prefs = data.get("preferences")
        if not isinstance(prefs, list):
            prefs = []
        return {
            "defaultProviderId": str(data.get("default_provider_id") or "ntq"),
            "contextPrompt": str(data.get("context_prompt") or ""),
            "contextPromptLane": str(data.get("context_prompt_lane") or "context"),
            "contextPromptMaxChars": int(data.get("context_prompt_max_chars") or 2000),
            "preferences": [str(item) for item in prefs if str(item or "").strip()],
            "preferenceMaxRules": int(data.get("preference_max_rules") or 40),
            "preferenceMaxChars": int(data.get("preference_max_chars") or 200),
        }


impl = AgentImplementer()
