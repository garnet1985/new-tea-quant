"""Read-only probes for provider auth and rate limits (no provider init)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Type

from core.infra.project_context import PathManager
from core.modules.data_source.base_class.base_provider import BaseProvider


def probe_provider_auth_configured(provider_class: Type[Any]) -> bool:
    """Return whether required auth credentials appear configured for a provider class."""
    if not getattr(provider_class, "requires_auth", False):
        return True

    auth_type = getattr(provider_class, "auth_type", None)
    provider_name = str(getattr(provider_class, "provider_name", "") or "").strip()

    if auth_type == "token":
        if provider_name == "tushare":
            auth_token_path = PathManager.data_source_provider("tushare") / "auth_token.txt"
            if auth_token_path.exists():
                try:
                    token = auth_token_path.read_text(encoding="utf-8").strip()
                    if token:
                        return True
                except OSError:
                    pass
            return bool(os.getenv("TUSHARE_TOKEN"))

        env_name = f"{provider_name.upper()}_TOKEN" if provider_name else None
        return bool(env_name and os.getenv(env_name))

    if auth_type == "api_key":
        env_name = f"{provider_name.upper()}_API_KEY" if provider_name else None
        return bool(env_name and os.getenv(env_name))

    return True


def resolve_api_rate_limit_per_minute(
    provider_class: Type[Any],
    method: str,
    *,
    default_limit: int = 60,
) -> int:
    """Resolve per-minute rate limit for a provider API method."""
    api_limits = getattr(provider_class, "api_limits", None) or {}
    default_rate = getattr(provider_class, "default_rate_limit", None)
    raw = api_limits.get(method, default_rate)
    if raw is not None:
        try:
            value = int(raw)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return default_limit


def summarize_provider_auth(
    provider_names: List[str],
    provider_classes: Dict[str, Type[Any]],
) -> Dict[str, Any]:
    """Aggregate auth requirements and readiness across provider names."""
    required: List[str] = []
    missing: List[str] = []

    for name in provider_names:
        cls = provider_classes.get(name)
        if cls is None:
            continue
        if not getattr(cls, "requires_auth", False):
            continue
        required.append(name)
        if not probe_provider_auth_configured(cls):
            missing.append(name)

    requires_auth = bool(required)
    auth_ready = not missing
    hint = ""
    if missing:
        if "tushare" in missing:
            provider_path = PathManager.data_source_provider("tushare")
            hint = (
                f"请配置 Tushare Token：{provider_path}/auth_token.txt "
                "或环境变量 TUSHARE_TOKEN"
            )
        else:
            hint = f"请配置以下 Provider 的认证信息：{', '.join(missing)}"

    return {
        "requires_auth": requires_auth,
        "auth_ready": auth_ready,
        "missing_auth_providers": missing,
        "auth_hint": hint,
    }


def min_rate_limit_per_minute(
    apis: Dict[str, Any],
    provider_classes: Dict[str, Type[Any]],
    *,
    default_limit: int = 60,
) -> Optional[int]:
    """Return the minimum configured per-minute limit across handler APIs."""
    limits: List[int] = []
    for api_cfg in apis.values():
        provider_name = str(getattr(api_cfg, "provider_name", "") or "").strip()
        method = str(getattr(api_cfg, "method", "") or "").strip()
        if not provider_name or not method:
            continue
        cls = provider_classes.get(provider_name)
        if cls is None:
            limits.append(default_limit)
            continue
        limits.append(
            resolve_api_rate_limit_per_minute(cls, method, default_limit=default_limit)
        )
    if not limits:
        return None
    return min(limits)
