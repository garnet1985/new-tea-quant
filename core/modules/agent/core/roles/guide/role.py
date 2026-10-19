"""介绍者入口：架构讲解（白名单文档）或一般产品问答（wiki + 只读工具）。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.modules.agent.core.navigator import patterns as nav_patterns
from core.modules.agent.core.loop_runtime import ask, decision, json_object, usable_reply
from core.modules.agent.core.roles.guide.docs import load_allowlisted_docs
from core.modules.agent.core.roles.guide.prompt import (
    ARCH_SYSTEM,
    WIKI_READ_TOOLS,
    wiki_system_prompt,
)
from core.modules.agent.core.session_store import update_state_from_tool
from core.modules.agent.core.tool_catalog import ToolCatalog
from core.modules.agent.core.tool_runner import run_tool

_GATE_MAX_STEPS = 4
logger = logging.getLogger(__name__)


def run_encyclopedia(
    text: str,
    *,
    memory: List[Dict[str, str]],
    provider_id: str,
    billing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """拼说明书轻问答（无工具循环）；通道无关。"""
    from core.modules.agent.core.knowledge.stitch import build_encyclopedia_messages

    def _pick(messages: List[Dict[str, str]]) -> str:
        return ask(
            messages,
            provider_id=provider_id,
            ntq_mode="",
            billing=billing,
            max_tokens=256,
        )

    # memory 已含近期轮次；百科拼装再用同一批当 history
    history = [m for m in memory if m.get("role") in {"user", "assistant"}]
    messages = build_encyclopedia_messages(
        text,
        history=history,
        pick_complete=_pick,
    )
    # 避免与 memory 重复：build 已含 history；不再 prepend memory
    raw = ask(
        messages,
        provider_id=provider_id,
        ntq_mode="",
        billing=billing,
        max_tokens=1600,
    )
    reply = usable_reply(raw) or str(raw or "").strip()
    if not reply:
        reply = "暂时无法回答。你可以换个问法，或在设置里确认该供应商的 API Key。"
    return {"reply": reply, "handoff": False}


def run_architecture(
    text: str,
    *,
    memory: List[Dict[str, str]],
    provider_id: str,
    billing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """架构路径：注入 arch 白名单，ask 模型作答，不 handoff。"""
    docs = load_allowlisted_docs("docs_arch.allowlist")
    user = (
        f"用户问题：\n{text}\n\n"
        f"说明书摘录：\n{docs or '（白名单文档暂不可用，请仅依据已知 NTQ 公开事实作答，不确定就说明。）'}"
    )
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": ARCH_SYSTEM},
        *memory,
        {"role": "user", "content": user},
    ]
    raw = ask(
        messages,
        provider_id=provider_id,
        ntq_mode="ask",
        billing=billing,
        max_tokens=1600,
    )
    reply = usable_reply(raw) or str(raw or "").strip()
    if reply and nav_patterns.has_brand_leak(reply):
        reply = (
            "NTQ 是 New Tea Quant（新茶）的量化回测产品。"
            "下面按公开架构说明；细节以说明书为准。\n\n" + reply
        )
    if not reply:
        reply = (
            "暂时无法完整说明架构。你可以问「回测四步是什么」或「userspace 和 core 有什么区别」，"
            "或直接打开产品内的说明文档。"
        )
    return {"reply": reply, "handoff": False}


def run_wiki(
    catalog: ToolCatalog,
    text: str,
    *,
    memory: List[Dict[str, str]],
    provider_id: str,
    session_id: str,
    billing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """产品疑问：白皮书摘录 + 只读工具；可 handoff 给 worker。"""
    docs = load_allowlisted_docs("docs_wiki.allowlist")
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": wiki_system_prompt(catalog, docs_excerpt=docs),
        },
        *memory,
        {"role": "user", "content": text},
    ]
    for _ in range(_GATE_MAX_STEPS):
        raw = ask(
            messages,
            provider_id=provider_id,
            ntq_mode="ask",
            billing=billing,
        )
        payload = json_object(raw)
        if isinstance(payload, dict) and str(
            payload.get("handoff") or ""
        ).strip().lower() in {"work", "true", "1"}:
            return {"handoff": True}
        chosen = decision(raw, set(WIKI_READ_TOOLS))
        tool = str(chosen.get("tool") or "").strip()
        if tool:
            if tool not in WIKI_READ_TOOLS:
                return {"handoff": True}
            result = run_tool(catalog, tool, chosen.get("arguments") or {})
            update_state_from_tool(result, session_id)
            messages.append({"role": "assistant", "content": raw.strip()})
            messages.append(
                {
                    "role": "user",
                    "content": "工具结果：\n" + json.dumps(result, ensure_ascii=False),
                }
            )
            continue
        reply = usable_reply(chosen.get("reply"))
        if reply and nav_patterns.has_brand_leak(reply):
            logger.warning("guide wiki reply rejected for brand leak")
            messages.append({"role": "assistant", "content": raw.strip() or "{}"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "上一条穿帮了：NTQ 只能是 New Tea Quant（新茶），"
                        "不是 New Trading Question，也不是茶叶。"
                        "请按产品事实重答，"
                        '只输出 {"reply":"..."}。'
                    ),
                }
            )
            continue
        if reply and nav_patterns.FABRICATED_STRATEGY_RE.search(reply):
            logger.warning("guide wiki reply rejected for fabricated strategy labels")
            messages.append({"role": "assistant", "content": raw.strip() or "{}"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "上一条无效：禁止编造「策略 A/B/C」这类占位名。"
                        "请先调用 list_strategy_summaries，只用工具返回的真实 key 与数字回答；"
                        "没有报告就如实说暂无回测。"
                    ),
                }
            )
            continue
        if reply:
            return {"reply": reply}
        messages.append({"role": "assistant", "content": raw.strip() or "{}"})
        messages.append(
            {
                "role": "user",
                "content": (
                    "上一条无效：reply 不能为空，也不能是示例占位。"
                    "请针对用户原问题给出真实中文回答，"
                    '只输出 {"reply":"..."}。'
                ),
            }
        )
        continue
    return {"handoff": True}
