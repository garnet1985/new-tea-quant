"""AI 通道管理器：本机供应商发现、密钥与裸 complete（无官网业务）。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.infra.ai.contracts import AiError, CompleteResult, ProviderInfo
from core.infra.ai.core.openai_compatible_client import OpenAICompatibleClient
from core.infra.ai.core.provider_catalog import ProviderCatalog

# 与常见上游 chat 上限对齐；工具多轮时裁掉中间旧往返，不硬拒。
_MAX_COMPLETION_MESSAGES = 40


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
    if not cleaned:
        raise AiError("消息条数不正确")
    cleaned = _trim_completion_messages(cleaned, limit=_MAX_COMPLETION_MESSAGES)
    if not any(item["role"] == "user" for item in cleaned):
        raise AiError("至少要有一条用户消息")
    return cleaned


def _trim_completion_messages(
    cleaned: List[Dict[str, str]],
    *,
    limit: int = _MAX_COMPLETION_MESSAGES,
) -> List[Dict[str, str]]:
    """超限时保留开头连续 system + 末尾对话，避免工具多轮把通道打爆。"""
    limit = max(1, int(limit))
    if len(cleaned) <= limit:
        return cleaned
    head: List[Dict[str, str]] = []
    for item in cleaned:
        if item["role"] != "system":
            break
        head.append(item)
    if len(head) >= limit:
        head = head[: max(1, limit - 1)]
    rest = cleaned[len(head) :]
    budget = limit - len(head)
    trimmed = head + rest[-budget:]
    if not any(item["role"] == "user" for item in trimmed):
        for item in reversed(cleaned):
            if item["role"] == "user":
                if len(trimmed) >= limit:
                    trimmed = trimmed[:-1]
                insert_at = len(head)
                trimmed = trimmed[:insert_at] + [item] + trimmed[insert_at:]
                if len(trimmed) > limit:
                    trimmed = trimmed[:limit]
                break
    return trimmed


class AiChannelManager:
    """编排层：本机供应商通道；不注入说明书、不碰官网会员。"""

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
        info = self.get_provider(str(provider_id or "").strip())
        if info is None:
            raise AiError(f"未找到供应商：{provider_id}")
        try:
            self._catalog.save_api_key(info.directory, key)
        except ValueError as exc:
            detail = str(exc)
            if "too long" in detail:
                raise AiError("密钥过长") from None
            if "empty" in detail:
                raise AiError("密钥不能为空") from None
            raise AiError(f"无法写入供应商密钥：{info.provider_id}") from None
        except OSError:
            raise AiError(f"无法写入供应商密钥：{info.provider_id}") from None
        updated = self.get_provider(info.provider_id)
        if updated is None or not updated.has_api_key:
            raise AiError(f"密钥已写入但未能读取：{info.provider_id}")
        return updated

    def load_api_key(self, provider_id: str) -> Optional[str]:
        """读取本机供应商密钥；未配置或不存在则 ``None``。"""
        info = self.get_provider(str(provider_id or "").strip())
        if info is None:
            return None
        return self._catalog.load_api_key(info.directory)

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
        """按本机供应商目录做一次补全。官网会员通道不在本模块。"""
        # 先校验消息，避免缺供应商时掩盖格式错误
        _completion_messages(messages)
        provider = self._resolve_provider(provider_id)
        api_key = self._catalog.load_api_key(provider.directory)
        if not api_key:
            raise AiError(f"供应商未配置密钥：{provider.provider_id}")
        return self.complete_http(
            messages,
            base_url=provider.base_url,
            api_key=api_key,
            model=provider.model,
            provider_id=provider.provider_id,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            extra_body=extra_body,
        )

    def complete_http(
        self,
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
        """对任意 OpenAI 兼容端点发一次补全（供业务层注入已解析凭证）。"""
        cleaned = _completion_messages(messages)
        url = str(base_url or "").strip()
        key = str(api_key or "").strip()
        model_name = str(model or "").strip()
        if not url or not key or not model_name:
            raise AiError("补全端点参数不完整")
        kwargs: Dict[str, Any] = {
            "base_url": url,
            "api_key": key,
            "model": model_name,
            "messages": cleaned,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "extra_body": extra_body,
        }
        if timeout_seconds is not None:
            kwargs["timeout_seconds"] = float(timeout_seconds)
        reply, meta = self._client.complete_with_meta(**kwargs)
        resolved_model = str(meta.get("model") or model_name or "").strip()
        ntq = meta.get("ntq") if isinstance(meta.get("ntq"), dict) else None
        usage = meta.get("usage") if isinstance(meta.get("usage"), dict) else None
        return CompleteResult(
            reply=reply,
            provider_id=str(provider_id or "").strip() or "http",
            model=resolved_model or model_name,
            ntq=ntq,
            usage=usage,
        )

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
