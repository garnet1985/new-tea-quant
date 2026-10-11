"""会员通道：通用凭证在时，对话发给官网，模型密钥留在官网。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from core.infra.project_context import ProjectContext

DEFAULT_BASE_URL = "https://www.new-tea.cn/api/v1/ntq-ai"
ENV_BASE_URL = "NTQ_MEMBER_AI_BASE_URL"
CONFIG_NAME = "membership.json"
PROVIDER_ID = "ntq"
MODEL = "glm-4-flash"


def member_token() -> Optional[str]:
    """已装载的通用凭证。没有或格式不对时返回 None。"""
    from core.infra.membership import Membership

    return Membership.read()


def member_base_url() -> str:
    """官网 AI 根地址。环境变量优先，其次 userspace 配置，否则官网。"""
    env = os.environ.get(ENV_BASE_URL, "").strip()
    if env:
        return _clean_base(env)
    path = ProjectContext.path.get_user_config_root() / CONFIG_NAME
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            raw = str(data.get("ai_base_url") or "").strip()
            if raw:
                return _clean_base(raw)
    return DEFAULT_BASE_URL


def fetch_member_quota() -> Optional[dict]:
    """官网今日剩余回答次数。没有凭证或官网不可达时返回 None。"""
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
    try:
        limit = int(data.get("limit"))
        remaining = int(data.get("remaining"))
    except (TypeError, ValueError):
        return None
    if limit < 1:
        return None
    remaining = max(0, min(remaining, limit))
    return {"limit": limit, "remaining": remaining, "used": limit - remaining}


def _clean_base(value: str) -> str:
    text = str(value or "").strip().rstrip("/")
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return DEFAULT_BASE_URL
