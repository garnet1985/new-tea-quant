"""会员通道：通用凭证在时，对话发给官网，模型密钥留在官网。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from core.modules.ntq_external.conf.site_target import ai_base_url

PROVIDER_ID = "ntq"
MODEL = "glm-4-flash"


def member_token() -> Optional[str]:
    """已装载的通用凭证。没有或格式不对时返回 None。"""
    from core.infra.membership import Membership

    return Membership.read()


def member_base_url() -> str:
    """官网 AI 根地址：由统一的 ``base_url`` 派生。"""
    return ai_base_url()


def fetch_member_quota() -> Optional[dict]:
    """会员通道额度。优先读猫粮余额；旧版每日次数字段仍兼容。"""
    token = member_token()
    if not token:
        return None
    request = urllib.request.Request(
        member_base_url() + "/quota",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "NTQ-assistant/0.1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("balance") is not None or data.get("token_balance") is not None:
        try:
            balance = max(0.0, float(data.get("balance") or 0))
        except (TypeError, ValueError):
            return None
        try:
            token_balance = max(0, int(data.get("token_balance") or 0))
        except (TypeError, ValueError):
            token_balance = 0
        try:
            unit_tokens = max(1, int(data.get("unit_tokens") or 10000))
        except (TypeError, ValueError):
            unit_tokens = 10000
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        models = data.get("models") if isinstance(data.get("models"), dict) else {}
        return {
            "balance": round(balance, 2),
            "token_balance": token_balance,
            "unit_tokens": unit_tokens,
            "currency": str(data.get("currency") or "猫粮"),
            "models": models,
            "usage": usage,
            "remaining": round(balance, 2),
            "limit": max(round(balance, 2), 1),
            "used": 0,
        }
    try:
        limit = int(data.get("limit"))
        remaining = int(data.get("remaining"))
    except (TypeError, ValueError):
        return None
    if limit < 1:
        return None
    remaining = max(0, min(remaining, limit))
    return {"limit": limit, "remaining": remaining, "used": limit - remaining}


def fetch_member_usage(limit: int = 40) -> Optional[dict]:
    """会员猫粮流水。无凭证或官网不可达时返回 None。"""
    token = member_token()
    if not token:
        return None
    lim = max(1, min(100, int(limit or 40)))
    request = urllib.request.Request(
        member_base_url() + f"/usage?limit={lim}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "NTQ-assistant/0.1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("items")
    if not isinstance(items, list):
        return None
    try:
        catfood = float(data.get("catfood") or 0)
    except (TypeError, ValueError):
        catfood = 0.0
    return {
        "items": items,
        "catfood": round(catfood, 2),
        "catfood_free": data.get("catfood_free"),
        "catfood_paid": data.get("catfood_paid"),
        "currency": str(data.get("currency") or "猫粮"),
    }
