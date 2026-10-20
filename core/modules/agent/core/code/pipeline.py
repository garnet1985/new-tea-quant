"""运行循环：锁定 Provider → ask(Navigator) → work* → present?。

一个 Provider 干到底：补全一律 ``provider_id``；ntq 时模型调度在 Website。
开发可设 ``NTQ_AGENT_OWN_KEYS=1``：未传 provider 时默认本机 deepseek（仍是 own）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.conf.conf import PIPELINE_MAX_STEPS
from core.modules.agent.core.code.executor.guider import pipeline as guide_role
from core.modules.agent.core.code.executor.shared.present import (
    resolve_present_scenario,
    run_present,
)
from core.modules.agent.core.code.executor.shared.prompt_loader import load_prompt, load_reply
from core.modules.agent.core.code.executor.shared.use_tool import use_tool
from core.modules.agent.core.code.executor.worker import pipeline as worker_role
from core.modules.agent.core.code.navigator.advice_reply import format_strategy_summaries_reply
from core.modules.agent.core.code.navigator.router import route as navigate
from core.modules.agent.core.code.provider.provider import resolve_provider
from core.modules.agent.core.code.session.session_store import (
    append_turn,
    context_block,
    default_session_id,
    recent_turns,
    update_state_from_tool,
)
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog
from core.modules.agent.core.code.userspace.prompts import append_userspace_prompt


class RunLoop:
    """Provider → ask → work* → present?。"""

    def __init__(self, catalog: ToolCatalog) -> None:
        self._catalog = catalog

    def run(
        self,
        content: str,
        *,
        max_steps: int = PIPELINE_MAX_STEPS,
        session_id: Optional[str] = None,
        provider_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        text = str(content or "").strip()
        if not text:
            raise AgentError("消息不能为空")
        steps = int(max_steps)
        if steps < 1 or steps > PIPELINE_MAX_STEPS:
            raise AgentError(f"一轮最多 {PIPELINE_MAX_STEPS} 次模型调用")
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
            reply = load_reply("intro")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "advice":
            result = use_tool(self._catalog, "list_strategy_summaries", {})
            update_state_from_tool(result, sid)
            reply = format_strategy_summaries_reply(result)
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "out_of_scope":
            reply = load_reply("out_of_scope")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "guide_arch":
            outcome = guide_role.run_architecture(
                text, memory=memory, provider_id=pid, billing=billing
            )
            reply = _maybe_present(
                text,
                outcome,
                provider_id=pid,
                billing=billing,
            )
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        if decision.kind == "worker":
            outcome = worker_role.run(
                self._catalog,
                text,
                memory=memory,
                max_steps=steps,
                session_id=sid,
                provider_id=pid,
                billing=billing,
            )
            reply = _maybe_present(
                text,
                outcome,
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
            reply = _maybe_present(
                text,
                guide,
                provider_id=pid,
                billing=billing,
            )
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text, reply=reply, channel=pid, handoff=False, session_id=sid
            )
            return _run_result(reply, handoff=False, billing=billing)

        outcome = worker_role.run(
            self._catalog,
            text,
            memory=memory,
            max_steps=steps,
            session_id=sid,
            provider_id=pid,
            billing=billing,
        )
        # guide 已读过的工具痕迹并入 worker，便于 present 识别 scenario
        merged = _merge_tools_seen(guide.get("tools_seen"), outcome.get("tools_seen"))
        outcome = {**outcome, "tools_seen": merged}
        reply = _maybe_present(
            text,
            outcome,
            provider_id=pid,
            billing=billing,
        )
        append_turn(user=text, reply=reply, channel=pid, handoff=True, session_id=sid)
        return _run_result(reply, handoff=True, billing=billing)


def _maybe_present(
    user_text: str,
    outcome: Mapping[str, Any] | str,
    *,
    provider_id: str,
    billing: Dict[str, Any],
) -> str:
    if isinstance(outcome, str):
        conclusion = outcome.strip()
        tools_seen: Sequence[Mapping[str, Any]] = ()
    else:
        conclusion = str(outcome.get("reply") or "").strip()
        raw_tools = outcome.get("tools_seen")
        tools_seen = raw_tools if isinstance(raw_tools, list) else ()
    if not conclusion:
        return ""
    scenario = resolve_present_scenario(user_text, tools_seen)
    return run_present(
        conclusion=conclusion,
        scenario=scenario,
        provider_id=provider_id,
        billing=billing,
    )


def _merge_tools_seen(
    left: Any,
    right: Any,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for block in (left, right):
        if not isinstance(block, list):
            continue
        for row in block:
            if isinstance(row, dict):
                out.append(row)
    return out


def _memory_messages(session_id: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    block = context_block(session_id)
    preamble = append_userspace_prompt(
        load_prompt("global/session_preamble.md").rstrip(),
        "context",
    )
    # 有会话状态或用户 context 片段时注入 system
    if block or "用户扩展" in preamble:
        content = preamble if not block else preamble + "\n" + block
        messages.append({"role": "system", "content": content})
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
    # mode：给 UI/BFF 的简写（是否进过执行者）；语义上等于 handoff，不是 ntq.phase。
    used_worker = bool(handoff)
    return {
        "reply": str(reply or ""),
        "handoff": used_worker,
        "mode": "work" if used_worker else "ask",
        "catfood_spent": catfood_spent,
        "balance": balance_out,
    }
