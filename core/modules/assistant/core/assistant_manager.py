"""助理内部管理器：协调供应商发现、百科挑选与调用。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.assistant.contracts import AssistantError, ChatResult, ProviderInfo
from core.modules.assistant.core.context_library import (
    ContextDoc,
    catalog_text,
    compose_knowledge,
    docs_of_kind,
    list_context_docs,
    parse_picked_ids,
    pick_optional_docs,
    should_ask_model_to_pick,
)
from core.modules.assistant.core.openai_compatible_client import OpenAICompatibleClient
from core.modules.assistant.core.provider_catalog import ProviderCatalog

_HISTORY_LIMIT = 16
_ALLOWED_ROLES = frozenset({"user", "assistant"})
_SYSTEM_PROMPT = (
    "你是 New Tea Quant（NTQ，中文名「新茶」）内置助理，对外也自称「新茶」。"
    "「新茶 / NTQ / New Tea Quant」指本量化产品与框架，不是茶叶。"
    "帮助用户理解 NTQ 术语与原则、撰写与修改策略、解读回测或选股报告，并回答金融相关问题。"
    "回答简洁、准确，使用 Markdown。"
    "优先依据下方说明书。说明书没有的不要编造，并说明不确定。"
)
_SELECT_PROMPT = (
    "你是 NTQ 文档调度。根据用户问题，从目录中选出最多 3 个最相关的文档 id。"
    '只输出 JSON 字符串数组，例如 ["know_how/config_strategy_settings"]。'
    "没有相关文档就输出 []。不要解释。\n\n目录：\n"
)


def _member_channel():
    """官网通道。模块不在时返回 None，助理改走本机密钥。"""
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
        raise AssistantError("消息必须是列表")
    cleaned: List[Dict[str, str]] = []
    for raw in messages:
        if not isinstance(raw, Mapping):
            raise AssistantError("消息格式不正确")
        role = str(raw.get("role") or "").strip()
        text = str(raw.get("content") or "").strip()
        if role not in {"system", "user", "assistant"} or not text:
            raise AssistantError("消息格式不正确")
        if len(text) > 80000:
            raise AssistantError("单条消息过长")
        cleaned.append({"role": role, "content": text})
    if not cleaned or len(cleaned) > 40:
        raise AssistantError("消息条数不正确")
    if not any(item["role"] == "user" for item in cleaned):
        raise AssistantError("至少要有一条用户消息")
    return cleaned


def _normalize_history(
    history: Optional[Sequence[Mapping[str, str]]],
) -> List[Dict[str, str]]:
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

    def set_api_key(self, provider_id: str, api_key: str) -> ProviderInfo:
        """把密钥写入已发现供应商的 ``api_key.txt``，返回更新后的快照。"""
        key = str(api_key or "").strip()
        if not key:
            raise AssistantError("密钥不能为空")
        if len(key) > 4096:
            raise AssistantError("密钥过长")
        info = self.get_provider(str(provider_id or "").strip())
        if info is None:
            raise AssistantError(f"未找到供应商：{provider_id}")
        try:
            self._catalog.save_api_key(info.directory, key)
        except (OSError, ValueError):
            raise AssistantError(f"无法写入供应商密钥：{info.provider_id}") from None
        updated = self.get_provider(info.provider_id)
        if updated is None or not updated.has_api_key:
            raise AssistantError(f"密钥已写入但未能读取：{info.provider_id}")
        return updated

    def chat(
        self,
        content: str,
        *,
        provider_id: Optional[str] = None,
        history: Optional[Sequence[Mapping[str, str]]] = None,
    ) -> ChatResult:
        """完成一轮用户消息。未指定供应商且已装载通用凭证时走官网。"""
        text = str(content or "").strip()
        if not text:
            raise AssistantError("消息不能为空")
        route = self._route(provider_id)
        try:
            reply = self._answer(text, history, route)
        except AssistantError as exc:
            if route["via"] == "member":
                raise AssistantError(_member_error(str(exc))) from None
            raise
        return ChatResult(
            reply=reply,
            provider_id=route["provider_id"],
            model=route["model"],
        )

    def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        provider_id: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> ChatResult:
        """按给定消息做一次补全。不注入百科，也不挑选文档。"""
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
        except AssistantError as exc:
            if route["via"] == "member":
                raise AssistantError(_member_error(str(exc))) from None
            raise
        model = str(meta.get("model") or route["model"] or "").strip()
        ntq = meta.get("ntq") if isinstance(meta.get("ntq"), dict) else None
        usage = meta.get("usage") if isinstance(meta.get("usage"), dict) else None
        return ChatResult(
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
                    raise AssistantError("会员通道不可用。")
                raise AssistantError("还没有装载会员通用凭证。请到设置 → 会员装载。")
        provider = self._resolve_provider(explicit or None)
        api_key = self._catalog.load_api_key(provider.directory)
        if not api_key:
            raise AssistantError(f"供应商未配置密钥：{provider.provider_id}")
        return {
            "via": "local",
            "provider_id": provider.provider_id,
            "base_url": provider.base_url,
            "api_key": api_key,
            "model": provider.model,
        }

    def _answer(
        self,
        text: str,
        history: Optional[Sequence[Mapping[str, str]]],
        route: Mapping[str, str],
    ) -> str:
        knowledge = self._knowledge_for_question(
            text,
            base_url=route["base_url"],
            api_key=route["api_key"],
            model=route["model"],
        )
        system = _SYSTEM_PROMPT
        if knowledge:
            system = _SYSTEM_PROMPT + "\n\n# NTQ 说明书\n\n" + knowledge
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system},
            *_normalize_history(history),
            {"role": "user", "content": text},
        ]
        return self._client.complete(
            base_url=route["base_url"],
            api_key=route["api_key"],
            model=route["model"],
            messages=messages,
        )

    def _knowledge_for_question(
        self,
        question: str,
        *,
        base_url: str,
        api_key: str,
        model: str,
    ) -> str:
        docs = list_context_docs()
        global_docs = docs_of_kind(docs, "global")
        optional = [item for item in docs if item.kind != "global"]
        picked_ids: Optional[List[str]] = None
        if should_ask_model_to_pick(optional):
            picked_ids = self._pick_doc_ids(
                question,
                optional,
                base_url=base_url,
                api_key=api_key,
                model=model,
            )
        selected = pick_optional_docs(question, optional, picked_ids=picked_ids)
        return compose_knowledge(global_docs, selected)

    def _pick_doc_ids(
        self,
        question: str,
        optional: Sequence[ContextDoc],
        *,
        base_url: str,
        api_key: str,
        model: str,
    ) -> List[str]:
        catalog = catalog_text(optional)
        if not catalog:
            return []
        try:
            raw = self._client.complete(
                base_url=base_url,
                api_key=api_key,
                model=model,
                messages=[
                    {"role": "system", "content": _SELECT_PROMPT + catalog},
                    {"role": "user", "content": question},
                ],
                max_tokens=256,
                temperature=0.0,
            )
        except AssistantError:
            return []
        return parse_picked_ids(raw, {item.doc_id for item in optional})

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
                raise AssistantError("没有可用的供应商：请在设置中填写 API Key")
            info = ready[0]
        if not info.enabled:
            raise AssistantError(f"供应商已禁用：{info.provider_id}")
        if not info.has_api_key:
            raise AssistantError(f"供应商未配置密钥：{info.provider_id}")
        return info
