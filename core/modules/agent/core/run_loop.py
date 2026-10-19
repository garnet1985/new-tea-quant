"""运行循环编排。产品默认会员通道 ntq；本机拼 context 并执行工具。

官网代理只转发文本，不转发 tools 字段。模型用 JSON 交出调用单，本机执行后再把摘要送回去。
开发可用环境变量 NTQ_AGENT_OWN_KEYS=1 改走本机智谱门 + DeepSeek 做事（不扣猫粮）。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.gate import patterns as gate_patterns
from core.modules.agent.core.gate.advice_reply import format_strategy_summaries_reply
from core.modules.agent.core.gate.router import route as route_intent
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
_PRODUCT_PROVIDER = "ntq"
_OWN_GATE_PROVIDER = "zhipu"
_OWN_WORK_PROVIDER = "deepseek"
_OWN_KEYS_ENV = "NTQ_AGENT_OWN_KEYS"
_PRODUCT_INTRO = gate_patterns.PRODUCT_INTRO
_OUT_OF_SCOPE_WEB_REPLY = gate_patterns.OUT_OF_SCOPE_WEB_REPLY
_BYOK_NO_WORKER = (
    "当前使用的是本机 API Key 通道，只能做说明书与基础问答，"
    "不能写策略或跑回测。请切换到「NTQ AI」（会员）后再试。"
)
logger = logging.getLogger(__name__)


class RunLoop:
    """模型点名与本机执行的循环。"""

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
        gate_provider, work_provider = _resolve_providers(provider_id)
        byok = _is_byok(gate_provider)
        billing: Dict[str, Any] = {"catfood_spent": 0.0, "balance": None}
        decision = route_intent(text)

        if decision.kind == "identity":
            reply = _PRODUCT_INTRO
            append_turn(
                user=text, reply=reply, channel=gate_provider, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "advice":
            result = run_tool(self._catalog, "list_strategy_summaries", {})
            update_state_from_tool(result, sid)
            reply = format_strategy_summaries_reply(result)
            append_turn(
                user=text, reply=reply, channel=gate_provider, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "out_of_scope":
            reply = _OUT_OF_SCOPE_WEB_REPLY
            append_turn(
                user=text, reply=reply, channel=gate_provider, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        # BYOK：门禁后只走百科拼装，不跑工具 / worker
        if byok:
            if decision.kind == "worker":
                reply = _BYOK_NO_WORKER
                append_turn(
                    user=text,
                    reply=reply,
                    channel=gate_provider,
                    handoff=False,
                    session_id=sid,
                )
                return _run_result(reply, handoff=False, billing=billing)
            if decision.kind == "guide_arch":
                outcome = guide_role.run_architecture(
                    text,
                    memory=memory,
                    provider_id=gate_provider,
                    billing=billing,
                )
            else:
                outcome = guide_role.run_encyclopedia(
                    text,
                    memory=memory,
                    provider_id=gate_provider,
                    billing=billing,
                )
            reply = str(outcome.get("reply") or "").strip()
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text, reply=reply, channel=gate_provider, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "guide_arch":
            outcome = guide_role.run_architecture(
                text,
                memory=memory,
                provider_id=gate_provider,
                billing=billing,
            )
            reply = str(outcome.get("reply") or "").strip()
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text, reply=reply, channel=gate_provider, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "worker":
            reply = worker_role.run(
                self._catalog,
                text,
                memory=memory,
                max_steps=steps,
                session_id=sid,
                provider_id=work_provider,
                billing=billing,
            )
            append_turn(
                user=text, reply=reply, channel=work_provider, handoff=True, session_id=sid
            )
            return _run_result(reply, handoff=True, billing=billing)

        gate = guide_role.run_wiki(
            self._catalog,
            text,
            memory=memory,
            provider_id=gate_provider,
            session_id=sid,
            billing=billing,
        )
        if not gate.get("handoff"):
            reply = str(gate.get("reply") or "").strip()
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text, reply=reply, channel=gate_provider, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        reply = worker_role.run(
            self._catalog,
            text,
            memory=memory,
            max_steps=steps,
            session_id=sid,
            provider_id=work_provider,
            billing=billing,
        )
        append_turn(
            user=text, reply=reply, channel=work_provider, handoff=True, session_id=sid
        )
        return _run_result(reply, handoff=True, billing=billing)


def _memory_messages(session_id: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    block = context_block(session_id)
    if block:
        messages.append(
            {
                "role": "system",
                "content": "以下是跨会话偏好和当前任务状态，回答时遵守：\n" + block,
            }
        )
    messages.extend(recent_turns(session_id))
    return messages


def _own_keys() -> bool:
    return os.environ.get(_OWN_KEYS_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _resolve_providers(provider_id: Optional[str]) -> Tuple[str, str]:
    """返回 (gate_provider, work_provider)。"""
    explicit = str(provider_id or "").strip()
    if explicit and explicit != _PRODUCT_PROVIDER:
        # BYOK：问答与（若放开）做事都用同一本机供应商
        return explicit, explicit
    if _own_keys():
        return _OWN_GATE_PROVIDER, _OWN_WORK_PROVIDER
    return _PRODUCT_PROVIDER, _PRODUCT_PROVIDER


def _is_byok(provider_id: str) -> bool:
    """会员 ntq 与开发 OWN_KEYS 双供应商不算 BYOK 轻问答限制。"""
    pid = str(provider_id or "").strip()
    if not pid or pid == _PRODUCT_PROVIDER:
        return False
    if _own_keys() and pid in {_OWN_GATE_PROVIDER, _OWN_WORK_PROVIDER}:
        return False
    return True


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
