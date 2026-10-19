"""AI 通道 implementer — 懒加载 ``infra.ai``。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.bff.APIs.platform.ai.helpers import provider_item


def _status_for_ai_error(exc: Exception) -> int:
    msg = str(exc)
    if "用完" in msg:
        return 429
    if "凭证" in msg:
        return 401
    if any(
        token in msg
        for token in ("空", "未找到", "没有可用", "未配置", "已禁用", "无法写入", "过长")
    ):
        return 400
    return 502


class AiImplementer:
    def __init__(self) -> None:
        self._AiChannel = None
        self._AiError = None

    def lazy_load(self) -> "AiImplementer":
        if self._AiChannel is None:
            from core.infra.ai import AiChannel
            from core.infra.ai.contracts import AiError

            self._AiChannel = AiChannel
            self._AiError = AiError
        return self

    def list_providers(self) -> Dict[str, Any]:
        assert self._AiChannel is not None
        items = [provider_item(info) for info in self._AiChannel.list_providers()]
        return {"items": items}

    def set_api_key(
        self,
        provider_id: str,
        api_key: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._AiChannel is not None
        assert self._AiError is not None
        try:
            info = self._AiChannel.set_api_key(provider_id, api_key)
        except self._AiError as exc:
            return None, str(exc), _status_for_ai_error(exc)
        return provider_item(info), None, 200


impl = AiImplementer()
