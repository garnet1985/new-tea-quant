"""运行循环：锁定 Provider → Navigator → 流向执行。

一个 Provider 干到底：补全一律 ``provider_id``；ntq 时模型调度在 Website。
开发可设 ``NTQ_AGENT_OWN_KEYS=1``：未传 provider 时默认本机 deepseek（仍是 own）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.navigator.advice_reply import format_strategy_summaries_reply
from core.modules.agent.core.navigator.router import route as navigate
from core.modules.agent.core.prompt_store import load_prompt, load_reply
from core.modules.agent.core.provider import resolve_provider
from core.modules.agent.core.roles.guide import role as guide_role
from core.modules.agent.core.roles.worker import role as worker_role
from core.modules.agent.core.session_store import (
    append_turn,
    context_block,
    default_session_id,
    recent_turns,
    update_state_from_tool,
)
from core.modules.agent.core.tool_catalog import ToolCatalog
from core.modules.agent.core.tool_runner import run_tool

_MAX_STEPS = 14
logger = logging.getLogger(__name__)


class RunLoop:
    """Provider → Navigator → 本机执行。"""

    def __init__(self, catalog: ToolCatalog) -> None:
        self._catalog = catalog

    def run(
        self,
        content: str,
        *,
        max_steps: int = _MAX_STEPS,
        session_id: Optional[str] = None,
        provider_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        text = str(content or "").strip()
        if not text:
            raise AgentError("消息不能为空")
        steps = int(max_steps)
        if steps < 1 or steps > _MAX_STEPS:
            raise AgentError(f"一轮最多 {_MAX_STEPS} 次模型调用")
        sid = str(session_id or "").strip() or default_session_id()
        memory = _memory_messages(sid)
        provider = resolve_provider(provider_id)
        if not provider.available:
            raise AgentError(
                provider.unavailable_reason or "当前 Provider 不可用，请检查配置。"
            )
        pid = provider.id
        billing: Dict[str, Any] = {"catfood_spent": 0.0, "balance": None}

        decision = navigate(text, provider_id=pid)

        if decision.kind == "identity":
            reply = load_reply("product_intro")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "advice":
            result = run_tool(self._catalog, "list_strategy_summaries", {})
            update_state_from_tool(result, sid)
            reply = format_strategy_summaries_reply(result)
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "out_of_scope":
            reply = load_reply("out_of_scope_web")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "guide_arch":
            outcome = guide_role.run_architecture(
                text, memory=memory, provider_id=pid, billing=billing
            )
            reply = str(outcome.get("reply") or "").strip()
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "worker":
            reply = worker_role.run(
                self._catalog,
                text,
                memory=memory,
                max_steps=steps,
                session_id=sid,
                provider_id=pid,
                billing=billing,
            )
            append_turn(
                user=text, reply=reply, channel=pid, handoff=True, session_id=sid
            )
            return _run_result(reply, handoff=True, billing=billing)

        guide = guide_role.run_wiki(
            self._catalog,
            text,
            memory=memory,
            provider_id=pid,
            session_id=sid,
            billing=billing,
        )
        if not guide.get("handoff"):
            reply = str(guide.get("reply") or "").strip()
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        reply = worker_role.run(
            self._catalog,
            text,
            memory=memory,
            max_steps=steps,
            session_id=sid,
            provider_id=pid,
            billing=billing,
        )
        append_turn(user=text, reply=reply, channel=pid, handoff=True, session_id=sid)
        return _run_result(reply, handoff=True, billing=billing)


def _memory_messages(session_id: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    block = context_block(session_id)
    if block:
        preamble = load_prompt("common/session_preamble.md").rstrip()
        messages.append(
            {
                "role": "system",
                "content": preamble + "\n" + block,
            }
        )
    messages.extend(recent_turns(session_id))
    return messages


def _run_result(
    reply: str,
    *,
    handoff: bool,
    billing: Dict[str, Any],
) -> Dict[str, Any]:
    spent = billing.get("catfood_spent")
    try:
        catfood_spent = round(max(0.0, float(spent or 0)), 2)
    except (TypeError, ValueError):
        catfood_spent = 0.0
    balance = billing.get("balance")
    try:
        balance_out = None if balance is None else round(max(0.0, float(balance)), 2)
    except (TypeError, ValueError):
        balance_out = None
    return {
        "reply": str(reply or ""),
        "handoff": bool(handoff),
        "mode": "work" if handoff else "ask",
        "catfood_spent": catfood_spent,
        "balance": balance_out,
    }
