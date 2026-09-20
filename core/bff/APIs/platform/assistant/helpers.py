"""Assistant HTTP DTO（camelCase；不含密钥）。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def provider_item(info: Any) -> Dict[str, Any]:
    return {
        "providerId": str(getattr(info, "provider_id", "") or ""),
        "baseUrl": str(getattr(info, "base_url", "") or ""),
        "model": str(getattr(info, "model", "") or ""),
        "enabled": bool(getattr(info, "enabled", False)),
        "hasApiKey": bool(getattr(info, "has_api_key", False)),
    }


def chat_item(*, reply: str, provider: Any) -> Dict[str, Any]:
    return {
        "reply": str(reply or ""),
        "providerId": str(getattr(provider, "provider_id", "") or ""),
        "model": str(getattr(provider, "model", "") or ""),
    }


def chat_request(payload: Mapping[str, Any]) -> Dict[str, Any]:
    content = str(payload.get("content") or "").strip()
    provider_id = str(payload.get("providerId") or payload.get("provider_id") or "").strip()
    history: List[Dict[str, str]] = []
    raw_history = payload.get("history")
    if isinstance(raw_history, list):
        for raw in raw_history:
            if not isinstance(raw, dict):
                continue
            role = str(raw.get("role") or "").strip()
            text = str(raw.get("content") or "").strip()
            if role in ("user", "assistant") and text:
                history.append({"role": role, "content": text})
    return {
        "content": content,
        "provider_id": provider_id or None,
        "history": history,
    }


def api_key_write_request(payload: Mapping[str, Any]) -> str:
    return str(payload.get("apiKey") or payload.get("api_key") or "").strip()
