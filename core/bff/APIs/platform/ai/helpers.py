"""AI 通道 HTTP DTO（camelCase；不含密钥）。"""

from __future__ import annotations

from typing import Any, Dict, Mapping


def provider_item(info: Any) -> Dict[str, Any]:
    return {
        "providerId": str(getattr(info, "provider_id", "") or ""),
        "baseUrl": str(getattr(info, "base_url", "") or ""),
        "model": str(getattr(info, "model", "") or ""),
        "enabled": bool(getattr(info, "enabled", False)),
        "hasApiKey": bool(getattr(info, "has_api_key", False)),
    }


def api_key_write_request(payload: Mapping[str, Any]) -> str:
    return str(payload.get("apiKey") or payload.get("api_key") or "").strip()
