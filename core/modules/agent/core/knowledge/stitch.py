"""把门禁后方的轻问答拼成完整 messages（含说明书）。"""

from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Optional, Sequence

from core.modules.agent.core.knowledge.context_library import (
    catalog_text,
    compose_knowledge,
    docs_of_kind,
    list_context_docs,
    parse_picked_ids,
    pick_optional_docs,
    should_ask_model_to_pick,
)

_HISTORY_LIMIT = 16
_ALLOWED_ROLES = frozenset({"user", "assistant"})
_SYSTEM_PROMPT = (
    "你是 New Tea Quant（NTQ，中文名「新茶」）内置助理，对外也自称「新茶」。"
    "「新茶 / NTQ / New Tea Quant」指本量化产品与框架，不是茶叶。"
    "帮助用户理解 NTQ 术语与原则、撰写与修改策略、解读回测或选股报告，并回答金融相关问题。"
    "回答简洁、准确，使用 Markdown。"
    "优先依据下方说明书。说明书没有的不要编造，并说明不确定。"
    "本通道不写策略文件、不启动回测；若用户要改代码或跑回测，请说明需使用会员 NTQ AI。"
)
_SELECT_PROMPT = (
    "你是 NTQ 文档调度。根据用户问题，从目录中选出最多 3 个最相关的文档 id。"
    '只输出 JSON 字符串数组，例如 ["know_how/config_strategy_settings"]。'
    "没有相关文档就输出 []。不要解释。\n\n目录：\n"
)

PickComplete = Callable[[List[Dict[str, str]]], str]


def build_encyclopedia_messages(
    question: str,
    *,
    history: Optional[Sequence[Mapping[str, str]]] = None,
    pick_complete: Optional[PickComplete] = None,
) -> List[Dict[str, str]]:
    """拼 system（含说明书）+ 历史 + 用户问题。"""
    text = str(question or "").strip()
    knowledge = _knowledge_for_question(text, pick_complete=pick_complete)
    system = _SYSTEM_PROMPT
    if knowledge:
        system = _SYSTEM_PROMPT + "\n\n# NTQ 说明书\n\n" + knowledge
    return [
        {"role": "system", "content": system},
        *_normalize_history(history),
        {"role": "user", "content": text},
    ]


def _knowledge_for_question(
    question: str,
    *,
    pick_complete: Optional[PickComplete],
) -> str:
    docs = list_context_docs()
    global_docs = docs_of_kind(docs, "global")
    optional = [item for item in docs if item.kind != "global"]
    picked_ids: Optional[List[str]] = None
    if pick_complete is not None and should_ask_model_to_pick(optional):
        picked_ids = _pick_doc_ids(question, optional, pick_complete=pick_complete)
    selected = pick_optional_docs(question, optional, picked_ids=picked_ids)
    return compose_knowledge(global_docs, selected)


def _pick_doc_ids(
    question: str,
    optional: Sequence,
    *,
    pick_complete: PickComplete,
) -> List[str]:
    catalog = catalog_text(optional)
    if not catalog:
        return []
    try:
        raw = pick_complete(
            [
                {"role": "system", "content": _SELECT_PROMPT + catalog},
                {"role": "user", "content": question},
            ]
        )
    except Exception:
        return []
    return parse_picked_ids(raw, {item.doc_id for item in optional})


def _normalize_history(
    history: Optional[Sequence[Mapping[str, str]]],
) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    if not history:
        return items
    for raw in history:
        if not isinstance(raw, Mapping):
            continue
        role = str(raw.get("role") or "").strip()
        text = str(raw.get("content") or "").strip()
        if role in _ALLOWED_ROLES and text:
            items.append({"role": role, "content": text})
    return items[-_HISTORY_LIMIT:]
