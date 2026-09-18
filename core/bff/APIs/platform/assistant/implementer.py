"""Assistant implementer — 懒加载 ``modules.assistant``。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.bff.APIs.platform.assistant.helpers import chat_item, provider_item


def _status_for_assistant_error(exc: Exception) -> int:
    msg = str(exc)
    if any(
        token in msg
        for token in ("空", "未找到", "没有可用", "未配置", "已禁用", "无法写入", "过长")
    ):
        return 400
    return 502


class AssistantImplementer:
    def __init__(self) -> None:
        self._Assistant = None
        self._AssistantError = None

    def lazy_load(self) -> "AssistantImplementer":
        if self._Assistant is None:
            from core.modules.assistant import Assistant
            from core.modules.assistant.contracts import AssistantError

            self._Assistant = Assistant
            self._AssistantError = AssistantError
        return self

    def list_providers(self) -> Dict[str, Any]:
        assert self._Assistant is not None
        items = [provider_item(info) for info in self._Assistant.list_providers()]
        return {"items": items}

    def chat(
        self,
        content: str,
        provider_id: Optional[str],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Assistant is not None
        assert self._AssistantError is not None
        if not content:
            return None, "消息不能为空", 400
        try:
            provider = self._resolve_provider(provider_id)
            reply = self._Assistant.chat(
                content,
                provider_id=provider.provider_id,
                history=history,
            )
        except self._AssistantError as exc:
            return None, str(exc), _status_for_assistant_error(exc)
        return chat_item(reply=reply, provider=provider), None, 200

    def set_api_key(
        self,
        provider_id: str,
        api_key: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        assert self._Assistant is not None
        assert self._AssistantError is not None
        try:
            info = self._Assistant.set_api_key(provider_id, api_key)
        except self._AssistantError as exc:
            return None, str(exc), _status_for_assistant_error(exc)
        return provider_item(info), None, 200

    def _resolve_provider(self, provider_id: Optional[str]):
        assert self._Assistant is not None
        if provider_id:
            info = self._Assistant.get_provider(provider_id)
            if info is None:
                raise self._AssistantError(f"未找到供应商：{provider_id}")
            return info
        ready = [
            item
            for item in self._Assistant.list_providers()
            if item.enabled and item.has_api_key
        ]
        if not ready:
            raise self._AssistantError(
                "没有可用的供应商：请在设置中填写 API Key"
            )
        return ready[0]


impl = AssistantImplementer()
