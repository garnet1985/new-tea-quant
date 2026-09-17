"""Assistant 门面 — 发现 userspace AI 供应商配置。"""

from __future__ import annotations

from typing import List, Optional

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


__all__ = ["Assistant"]
