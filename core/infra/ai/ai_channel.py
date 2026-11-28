"""AiChannel 门面 — 本机供应商发现、密钥与裸 complete。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Mapping

from core.infra.ai.contracts import CompleteResult, ProviderInfo
from core.infra.ai.core.ai_channel_manager import AiChannelManager


class AiChannel:
    """AI 通道门面。只服务本机供应商；官网会员通道见 ``modules.ntq_external``。"""

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
    def load_api_key(provider_id: str) -> Optional[str]:
        """读取本机供应商 API Key；未配置则 ``None``。供工具（如网页搜索）使用。"""
        return AiChannel._manager.load_api_key(provider_id)

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
        """按本机供应商做一次补全。不注入百科；不走官网会员。"""
        return AiChannel._manager.complete(
            messages,
            provider_id=provider_id,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            extra_body=extra_body,
        )

    @staticmethod
    def complete_http(
        messages: Sequence[Mapping[str, str]],
        *,
        base_url: str,
        api_key: str,
        model: str,
        provider_id: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> CompleteResult:
        """对任意 OpenAI 兼容端点补全；业务层注入已解析的地址与密钥。"""
        return AiChannel._manager.complete_http(
            messages,
            base_url=base_url,
            api_key=api_key,
            model=model,
            provider_id=provider_id,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            extra_body=extra_body,
        )


__all__ = ["AiChannel"]
