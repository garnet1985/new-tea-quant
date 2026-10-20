"""Executor 共用：模型补全与本轮猫粮记账。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.infra.ai import AiChannel
from core.infra.ai.contracts import AiError
from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.conf.conf import (
    ASK_DEFAULT_MAX_TOKENS,
    ASK_TEMPERATURE,
    PRODUCT_PROVIDER_ID,
)


def ask(
    messages: List[Dict[str, str]],
    *,
    provider_id: str,
    max_tokens: int = ASK_DEFAULT_MAX_TOKENS,
    timeout_seconds: Optional[float] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    ntq_phase: str = "",
    ntq_intent: Optional[str] = None,
    billing: Optional[Dict[str, Any]] = None,
) -> str:
    body = dict(extra_body or {})
    if provider_id == PRODUCT_PROVIDER_ID:
        phase = str(ntq_phase or "").strip().lower()
        if phase not in {"navigate", "act"}:
            raise AgentError("ntq 请求必须声明 ntq.phase=navigate|act")
        intent = None if phase == "navigate" else (
            str(ntq_intent).strip() if ntq_intent is not None else ""
        )
        if phase == "act" and not intent:
            intent = "guide"
        body["ntq"] = {
            "phase": phase,
            "intent": intent,
        }
    try:
        result = AiChannel.complete(
            messages,
            provider_id=provider_id,
            max_tokens=max_tokens,
            temperature=ASK_TEMPERATURE,
            timeout_seconds=timeout_seconds,
            extra_body=body or None,
        )
    except AiError as exc:
        raise AgentError(str(exc)) from None
    accumulate_billing(billing, result.ntq if isinstance(result.ntq, dict) else None)
    return result.reply


def accumulate_billing(
    billing: Optional[Dict[str, Any]],
    ntq: Optional[Dict[str, Any]],
) -> None:
    """Billing tracker：累加本轮 catfood_spent，刷新 balance 快照。"""
    if billing is None or not isinstance(ntq, dict):
        return
    try:
        spent = max(0.0, float(ntq.get("catfood_spent") or 0))
    except (TypeError, ValueError):
        spent = 0.0
    billing["catfood_spent"] = round(float(billing.get("catfood_spent") or 0) + spent, 2)
    for key in ("balance", "catfood"):
        if ntq.get(key) is None:
            continue
        try:
            billing["balance"] = round(max(0.0, float(ntq.get(key))), 2)
        except (TypeError, ValueError):
            pass
