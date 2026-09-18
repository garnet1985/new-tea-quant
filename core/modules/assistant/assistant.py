"""Assistant 门面 — 发现 userspace AI 供应商并发送聊天。"""

from __future__ import annotations

from typing import Dict, List, Optional

from core.modules.assistant.contracts import ProviderInfo
from core.modules.assistant.core.assistant_manager import AssistantManager


class Assistant:
    """AI 助理门面。"""

    _manager = AssistantManager()

    @staticmethod
    def list_providers() -> List[ProviderInfo]:
        """扫描 userspace 供应商目录，返回只读快照列表。"""
        return Assistant._manager.list_providers()

    @staticmethod
    def get_provider(provider_id: str) -> Optional[ProviderInfo]:
        """按目录名取一个供应商；找不到返回 ``None``。"""
        return Assistant._manager.get_provider(provider_id)

    @staticmethod
    def set_api_key(provider_id: str, api_key: str) -> ProviderInfo:
        """写入已发现供应商的密钥，返回不含明文的快照。"""
        return Assistant._manager.set_api_key(provider_id, api_key)

    @staticmethod
    def chat(
        content: str,
        *,
        provider_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """发送一句用户消息，返回助手文本。``history`` 为此前 user/assistant 轮次。"""
        return Assistant._manager.chat(
            content, provider_id=provider_id, history=history
        )


__all__ = ["Assistant"]
