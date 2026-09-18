"""助理内部管理器：协调供应商发现、百科挑选与调用。"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

from core.modules.assistant.contracts import AssistantError, ProviderInfo
from core.modules.assistant.core.context_library import (
    ContextDoc,
    catalog_text,
    compose_knowledge,
    docs_of_kind,
    list_context_docs,
    parse_picked_ids,
    pick_optional_docs,
    should_ask_model_to_pick,
)
from core.modules.assistant.core.openai_compatible_client import OpenAICompatibleClient
from core.modules.assistant.core.provider_catalog import ProviderCatalog

_HISTORY_LIMIT = 16
_ALLOWED_ROLES = frozenset({"user", "assistant"})
_SYSTEM_PROMPT = (
    "你是 New Tea Quant（NTQ）内置助理。"
    "帮助用户理解 NTQ 术语与原则、撰写与修改策略、解读回测或选股报告，并回答金融相关问题。"
    "回答简洁、准确，使用 Markdown。"
    "优先依据下方说明书。说明书没有的不要编造，并说明不确定。"
)
_SELECT_PROMPT = (
    "你是 NTQ 文档调度。根据用户问题，从目录中选出最多 3 个最相关的文档 id。"
    "只输出 JSON 字符串数组，例如 [\"know_how/config_strategy_settings\"]。"
    "没有相关文档就输出 []。不要解释。\n\n目录：\n"
)


def _normalize_history(history: Optional[Sequence[Mapping[str, str]]]) -> List[Dict[str, str]]:
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


class AssistantManager:
    """编排层：对外门面只经过本类访问实施层。"""

    def __init__(self, client: Optional[OpenAICompatibleClient] = None) -> None:
        self._catalog = ProviderCatalog()
        self._client = client or OpenAICompatibleClient()

    def list_providers(self) -> List[ProviderInfo]:
        """列出本机已发现的供应商快照。"""
        return self._catalog.list_providers()

    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        """按目录名取供应商；找不到返回 ``None``。"""
        return self._catalog.get_provider(provider_id)

    def set_api_key(self, provider_id: str, api_key: str) -> ProviderInfo:
        """把密钥写入已发现供应商的 ``api_key.txt``，返回更新后的快照。"""
        key = str(api_key or "").strip()
        if not key:
            raise AssistantError("密钥不能为空")
        if len(key) > 4096:
            raise AssistantError("密钥过长")
        info = self.get_provider(str(provider_id or "").strip())
        if info is None:
            raise AssistantError(f"未找到供应商：{provider_id}")
        try:
            self._catalog.save_api_key(info.directory, key)
        except (OSError, ValueError):
            raise AssistantError(f"无法写入供应商密钥：{info.provider_id}") from None
        updated = self.get_provider(info.provider_id)
        if updated is None or not updated.has_api_key:
            raise AssistantError(f"密钥已写入但未能读取：{info.provider_id}")
        return updated

    def chat(
        self,
        content: str,
        *,
        provider_id: Optional[str] = None,
        history: Optional[Sequence[Mapping[str, str]]] = None,
    ) -> str:
        """用已配置供应商完成一轮用户消息。"""
        text = str(content or "").strip()
        if not text:
            raise AssistantError("消息不能为空")
        provider = self._resolve_provider(provider_id)
        api_key = self._catalog.load_api_key(provider.directory)
        if not api_key:
            raise AssistantError(f"供应商未配置密钥：{provider.provider_id}")
        knowledge = self._knowledge_for_question(
            text,
            base_url=provider.base_url,
            api_key=api_key,
            model=provider.model,
        )
        system = _SYSTEM_PROMPT
        if knowledge:
            system = _SYSTEM_PROMPT + "\n\n# NTQ 说明书\n\n" + knowledge
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system},
            *_normalize_history(history),
            {"role": "user", "content": text},
        ]
        return self._client.complete(
            base_url=provider.base_url,
            api_key=api_key,
            model=provider.model,
            messages=messages,
        )

    def _knowledge_for_question(
        self,
        question: str,
        *,
        base_url: str,
        api_key: str,
        model: str,
    ) -> str:
        docs = list_context_docs()
        global_docs = docs_of_kind(docs, "global")
        optional = [item for item in docs if item.kind != "global"]
        picked_ids: Optional[List[str]] = None
        if should_ask_model_to_pick(optional):
            picked_ids = self._pick_doc_ids(
                question,
                optional,
                base_url=base_url,
                api_key=api_key,
                model=model,
            )
        selected = pick_optional_docs(question, optional, picked_ids=picked_ids)
        return compose_knowledge(global_docs, selected)

    def _pick_doc_ids(
        self,
        question: str,
        optional: Sequence[ContextDoc],
        *,
        base_url: str,
        api_key: str,
        model: str,
    ) -> List[str]:
        catalog = catalog_text(optional)
        if not catalog:
            return []
        try:
            raw = self._client.complete(
                base_url=base_url,
                api_key=api_key,
                model=model,
                messages=[
                    {"role": "system", "content": _SELECT_PROMPT + catalog},
                    {"role": "user", "content": question},
                ],
                max_tokens=256,
                temperature=0.0,
            )
        except AssistantError:
            return []
        return parse_picked_ids(raw, {item.doc_id for item in optional})

    def _resolve_provider(self, provider_id: Optional[str]) -> ProviderInfo:
        if provider_id:
            info = self.get_provider(str(provider_id).strip())
            if info is None:
                raise AssistantError(f"未找到供应商：{provider_id}")
        else:
            ready = [
                item
                for item in self.list_providers()
                if item.enabled and item.has_api_key
            ]
            if not ready:
                raise AssistantError(
                    "没有可用的供应商：请在设置中填写 API Key"
                )
            info = ready[0]
        if not info.enabled:
            raise AssistantError(f"供应商已禁用：{info.provider_id}")
        if not info.has_api_key:
            raise AssistantError(f"供应商未配置密钥：{info.provider_id}")
        return info
