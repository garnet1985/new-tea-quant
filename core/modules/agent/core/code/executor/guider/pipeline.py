"""介绍者入口：架构讲解（白名单文档）或一般产品问答（wiki + 只读工具）。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.modules.agent.core.code.conf.conf import (
    GUIDER_ARCH_MAX_TOKENS,
    GUIDER_MAX_STEPS,
)
from core.modules.agent.core.code.executor.guider.docs import load_allowlisted_docs
from core.modules.agent.core.code.executor.guider.prompt import (
    WIKI_READ_TOOLS,
    arch_system_prompt,
    wiki_system_prompt,
)
from core.modules.agent.core.code.executor.shared.complete import ask
from core.modules.agent.core.code.executor.shared.decision import (
    decision,
    json_object,
    usable_reply,
)
from core.modules.agent.core.code.executor.shared.present import record_tool_seen
from core.modules.agent.core.code.executor.shared.prompt_loader import (
    load_nudge,
    load_prompt,
    load_reply,
)
from core.modules.agent.core.code.executor.shared.use_tool import use_tool
from core.modules.agent.core.code.navigator import patterns as nav_patterns
from core.modules.agent.core.code.session.session_store import update_state_from_tool
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog

logger = logging.getLogger(__name__)


def run_architecture(
    text: str,
    *,
    memory: List[Dict[str, str]],
    provider_id: str,
    billing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """架构路径：注入 arch 白名单，ask 模型作答，不 handoff。"""
    docs = load_allowlisted_docs("docs_arch.allowlist") or load_reply("docs_unavailable")
    user = load_prompt(
        "specific/guider/arch_user.md",
        variables={"question": text, "docs": docs},
    ).rstrip()
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": arch_system_prompt()},
        *memory,
        {"role": "user", "content": user},
    ]
    raw = ask(
        messages,
        provider_id=provider_id,
        ntq_phase="act",
        ntq_intent="guide_arch",
        billing=billing,
        max_tokens=GUIDER_ARCH_MAX_TOKENS,
    )
    reply = usable_reply(raw) or str(raw or "").strip()
    if reply and nav_patterns.has_brand_leak(reply):
        reply = load_reply("arch_brand_prefix") + "\n\n" + reply
    if not reply:
        reply = load_reply("arch_unavailable")
    return {"reply": reply, "handoff": False, "tools_seen": []}


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
    tools_seen: List[Dict[str, Any]] = []
    for _ in range(GUIDER_MAX_STEPS):
        raw = ask(
            messages,
            provider_id=provider_id,
            ntq_phase="act",
            ntq_intent="guide",
            billing=billing,
        )
        payload = json_object(raw)
        if isinstance(payload, dict) and str(
            payload.get("handoff") or ""
        ).strip().lower() in {"work", "true", "1"}:
            return {"handoff": True, "tools_seen": tools_seen}
        chosen = decision(raw, set(WIKI_READ_TOOLS))
        tool = str(chosen.get("tool") or "").strip()
        if tool:
            if tool not in WIKI_READ_TOOLS:
                return {"handoff": True, "tools_seen": tools_seen}
            result = use_tool(catalog, tool, chosen.get("arguments") or {})
            record_tool_seen(tools_seen, tool, result)
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
                {"role": "user", "content": load_nudge("guide", "brand_leak")}
            )
            continue
        if reply and nav_patterns.FABRICATED_STRATEGY_RE.search(reply):
            logger.warning("guide wiki reply rejected for fabricated strategy labels")
            messages.append({"role": "assistant", "content": raw.strip() or "{}"})
            messages.append(
                {"role": "user", "content": load_nudge("guide", "fabricated_strategy")}
            )
            continue
        if reply:
            return {"reply": reply, "tools_seen": tools_seen}
        messages.append({"role": "assistant", "content": raw.strip() or "{}"})
        messages.append(
            {"role": "user", "content": load_nudge("guide", "empty_reply")}
        )
        continue
    return {"handoff": True, "tools_seen": tools_seen}
