"""用本地通用凭证向官网读取会员邮件代发额度。响应里没有凭证。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from core.modules.ntq_external.conf.site_target import member_mail_quota_url
from core.infra.utils.core.net.ssl_context import urlopen_https

# 与官网 ntq_mail 默认对齐（展示用；真实额度以 quota 接口为准）
DEFAULT_LIMIT = 30
MAX_OPPORTUNITIES_PER_MAIL = 80
POLICY_TEXT = (
    f"目前共可发 {DEFAULT_LIMIT} 封；只发到注册邮箱；"
    f"每封邮件里最多显示 {MAX_OPPORTUNITIES_PER_MAIL} 条机会"
)


def member_mail_quota() -> dict:
    """
    已装载凭证且官网可读时带上 limit / used / remaining。

    available 为 False 时 reason 为 missing / rejected / unreachable。
    policy 始终返回，方便 UI 在未登录时也展示规则。
    """
    base = _empty("missing")
    from core.infra.membership import Membership

    token = Membership.read()
    if not token:
        return base
    request = urllib.request.Request(
        member_mail_quota_url(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "NTQ/member-mail-quota",
        },
        method="GET",
    )
    try:
        with urlopen_https(request, timeout=8) as response:
            status = getattr(response, "status", 200)
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return _empty("rejected")
        return _empty("unreachable")
    except (urllib.error.URLError, TimeoutError, OSError):
        return _empty("unreachable")
    if status != 200:
        return _empty("unreachable")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _empty("unreachable")
    return _ok(data) or _empty("unreachable")


def _empty(reason: str) -> dict:
    return {
        "available": False,
        "reason": reason,
        "limit": DEFAULT_LIMIT,
        "used": None,
        "remaining": None,
        "unlimited": False,
        "policy": POLICY_TEXT,
    }


def _ok(data: object) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    unlimited = bool(data.get("unlimited"))
    used = _optional_nonneg_int(data.get("used"))
    if used is None:
        used = 0
    if unlimited:
        return {
            "available": True,
            "reason": None,
            "limit": None,
            "used": used,
            "remaining": None,
            "unlimited": True,
            "policy": POLICY_TEXT,
        }
    limit = _optional_nonneg_int(data.get("limit"))
    remaining = _optional_nonneg_int(data.get("remaining"))
    if limit is None:
        limit = DEFAULT_LIMIT
    if remaining is None:
        remaining = max(0, limit - used)
    return {
        "available": True,
        "reason": None,
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "unlimited": False,
        "policy": POLICY_TEXT,
    }


def _optional_nonneg_int(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return None
