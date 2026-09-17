"""助理内部管理器：协调供应商发现，后续还将协调调用。"""

from __future__ import annotations

from typing import List, Optional

from core.modules.assistant.contracts import ProviderInfo
from core.modules.assistant.core.provider_catalog import ProviderCatalog


class AssistantManager:
    """编排层：对外门面只经过本类访问实施层。"""

    def __init__(self) -> None:
        self._catalog = ProviderCatalog()

    def list_providers(self) -> List[ProviderInfo]:
        """列出本机已发现的供应商快照。"""
        return self._catalog.list_providers()

    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        """按目录名取供应商；找不到返回 ``None``。"""
        return self._catalog.get_provider(provider_id)
