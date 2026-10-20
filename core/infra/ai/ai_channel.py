"""AiChannel 门面 — 供应商发现、密钥与裸 complete。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.infra.ai.contracts import CompleteResult, ProviderInfo
from core.infra.ai.core.ai_channel_manager import AiChannelManager


class AiChannel:
    """AI 通道门面。不含百科拼装或业务门禁。"""

    _manager = AiChannelManager()

    @staticmethod
    def list_providers() -> List[ProviderInfo]:
        return AiChannel._manager.list_providers()

    @staticmethod
    def get_provider(provider_id: str) -> Optional[ProviderInfo]:
        return AiChannel._manager.get_provider(provider_id)

    @staticmethod
    def set_api_key(provider_id: str, api_key: str) -> ProviderInfo:
        return AiChannel._manager.set_api_key(provider_id, api_key)

    @staticmethod
    def complete(
        messages: List[Dict[str, str]],
        *,
        provider_id: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> CompleteResult:
        """按给定消息做一次补全。不注入百科。"""
        return AiChannel._manager.complete(
            messages,
            provider_id=provider_id,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            extra_body=extra_body,
        )


__all__ = ["AiChannel"]
