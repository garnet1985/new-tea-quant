"""AI 通道管理器：供应商发现、通道路由与裸 complete（无业务百科）。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.infra.ai.contracts import AiError, CompleteResult, ProviderInfo
from core.infra.ai.core.openai_compatible_client import OpenAICompatibleClient
from core.infra.ai.core.provider_catalog import ProviderCatalog


def _member_channel():
    try:
        from core.modules.ntq_external.ai import member_channel
    except ImportError:
        return None
    return member_channel


def _member_error(message: str) -> str:
    text = str(message or "").strip()
    if text.startswith("无法连接"):
        return "暂时连不上官网。可以先在设置里改用自己的密钥。"
    if "超时" in text:
        return "官网应答超时。可以先在设置里改用自己的密钥。"
    if text.startswith("供应商请求失败"):
        return "官网暂时不可用。可以先在设置里改用自己的密钥。"
    if text.startswith("供应商"):
        return "官网" + text[len("供应商") :]
    return text or "官网暂时不可用。可以先在设置里改用自己的密钥。"


def _completion_messages(messages: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
    if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes)):
        raise AiError("消息必须是列表")
    cleaned: List[Dict[str, str]] = []
    for raw in messages:
        if not isinstance(raw, Mapping):
            raise AiError("消息格式不正确")
        role = str(raw.get("role") or "").strip()
        text = str(raw.get("content") or "").strip()
        if role not in {"system", "user", "assistant"} or not text:
            raise AiError("消息格式不正确")
        if len(text) > 80000:
            raise AiError("单条消息过长")
        cleaned.append({"role": role, "content": text})
    if not cleaned or len(cleaned) > 40:
        raise AiError("消息条数不正确")
    if not any(item["role"] == "user" for item in cleaned):
        raise AiError("至少要有一条用户消息")
    return cleaned


class AiChannelManager:
    """编排层：只做通道，不注入说明书、不跑业务门禁。"""

    def __init__(self, client: Optional[OpenAICompatibleClient] = None) -> None:
        self._catalog = ProviderCatalog()
        self._client = client or OpenAICompatibleClient()

    def list_providers(self) -> List[ProviderInfo]:
        return self._catalog.list_providers()

    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        return self._catalog.get_provider(provider_id)

    def set_api_key(self, provider_id: str, api_key: str) -> ProviderInfo:
        key = str(api_key or "").strip()
        if not key:
            raise AiError("密钥不能为空")
        if len(key) > 4096:
            raise AiError("密钥过长")
        info = self.get_provider(str(provider_id or "").strip())
        if info is None:
            raise AiError(f"未找到供应商：{provider_id}")
        try:
            self._catalog.save_api_key(info.directory, key)
        except (OSError, ValueError):
            raise AiError(f"无法写入供应商密钥：{info.provider_id}") from None
        updated = self.get_provider(info.provider_id)
        if updated is None or not updated.has_api_key:
            raise AiError(f"密钥已写入但未能读取：{info.provider_id}")
        return updated

    def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        provider_id: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> CompleteResult:
        cleaned = _completion_messages(messages)
        route = self._route(provider_id)
        kwargs: Dict[str, Any] = {
            "base_url": route["base_url"],
            "api_key": route["api_key"],
            "model": route["model"],
            "messages": cleaned,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "extra_body": extra_body,
        }
        if timeout_seconds is not None:
            kwargs["timeout_seconds"] = float(timeout_seconds)
        try:
            reply, meta = self._client.complete_with_meta(**kwargs)
        except AiError as exc:
            if route["via"] == "member":
                raise AiError(_member_error(str(exc))) from None
            raise
        model = str(meta.get("model") or route["model"] or "").strip()
        ntq = meta.get("ntq") if isinstance(meta.get("ntq"), dict) else None
        usage = meta.get("usage") if isinstance(meta.get("usage"), dict) else None
        return CompleteResult(
            reply=reply,
            provider_id=route["provider_id"],
            model=model or route["model"],
            ntq=ntq,
            usage=usage,
        )

    def _route(self, provider_id: Optional[str]) -> Dict[str, str]:
        explicit = str(provider_id or "").strip()
        channel = _member_channel()
        member_id = channel.PROVIDER_ID if channel is not None else "ntq"
        if explicit == member_id or not explicit:
            token = channel.member_token() if channel is not None else None
            if token and channel is not None:
                return {
                    "via": "member",
                    "provider_id": channel.PROVIDER_ID,
                    "base_url": channel.member_base_url(),
                    "api_key": token,
                    "model": channel.MODEL,
                }
            if explicit == member_id:
                if channel is None:
                    raise AiError("会员通道不可用。")
                raise AiError("还没有装载会员通用凭证。请到设置 → 会员装载。")
        provider = self._resolve_provider(explicit or None)
        api_key = self._catalog.load_api_key(provider.directory)
        if not api_key:
            raise AiError(f"供应商未配置密钥：{provider.provider_id}")
        return {
            "via": "local",
            "provider_id": provider.provider_id,
            "base_url": provider.base_url,
            "api_key": api_key,
            "model": provider.model,
        }

    def _resolve_provider(self, provider_id: Optional[str]) -> ProviderInfo:
        if provider_id:
            info = self.get_provider(str(provider_id).strip())
            if info is None:
                raise AiError(f"未找到供应商：{provider_id}")
        else:
            ready = [
                item
                for item in self.list_providers()
                if item.enabled and item.has_api_key
            ]
            if not ready:
                raise AiError("没有可用的供应商：请在设置中填写 API Key")
            info = ready[0]
        if not info.enabled:
            raise AiError(f"供应商已禁用：{info.provider_id}")
        if not info.has_api_key:
            raise AiError(f"供应商未配置密钥：{info.provider_id}")
        return info
