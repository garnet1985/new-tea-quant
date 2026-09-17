"""助理内部管理器：协调供应商发现与调用。"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

from core.modules.assistant.contracts import AssistantError, ProviderInfo
from core.modules.assistant.core.openai_compatible_client import OpenAICompatibleClient
from core.modules.assistant.core.provider_catalog import ProviderCatalog

_HISTORY_LIMIT = 16
_ALLOWED_ROLES = frozenset({"user", "assistant"})
_SYSTEM_PROMPT = (
    "你是 New Tea Quant（NTQ）内置助理。"
    "帮助用户理解 NTQ 术语与原则、撰写与修改策略、解读回测或选股报告，并回答金融相关问题。"
    "回答简洁、准确；不确定时说明不确定。"
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
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *_normalize_history(history),
            {"role": "user", "content": text},
        ]
        return self._client.complete(
            base_url=provider.base_url,
            api_key=api_key,
            model=provider.model,
            messages=messages,
        )

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
                    "没有可用的供应商：请配置 enabled 且已填写 api_key.txt"
                )
            info = ready[0]
        if not info.enabled:
            raise AssistantError(f"供应商已禁用：{info.provider_id}")
        if not info.has_api_key:
            raise AssistantError(f"供应商未配置密钥：{info.provider_id}")
        return info
