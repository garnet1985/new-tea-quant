"""用本地通用凭证向官网要会员名、头像和点数。响应里没有凭证。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from core.modules.ntq_external.conf.endpoints import MEMBER_PROFILE_URL, REGISTER_URL


def member_profile() -> dict:
    """
    已登录时带上官网返回的 name / avatar / points。

    没有凭证，或官网拒绝这张凭证，signed_in 为 False，reason 为 missing 或 rejected。
    官网暂时连不上时 reason 为 unreachable，避免把网络故障说成未注册。
    """
    guest = _guest("missing")
    from core.infra.membership import Membership

    token = Membership.read()
    if not token:
        return guest
    request = urllib.request.Request(
        MEMBER_PROFILE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "NTQ/member-profile",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            status = getattr(response, "status", 200)
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return _guest("rejected")
        return _guest("unreachable")
    except (urllib.error.URLError, TimeoutError, OSError):
        return _guest("unreachable")
    if status != 200:
        return _guest("unreachable")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _guest("unreachable")
    return _signed_in(data) or _guest("unreachable")


def _guest(reason: str) -> dict:
    return {
        "signed_in": False,
        "register_url": REGISTER_URL,
        "name": None,
        "avatar": None,
        "points": None,
        "reason": reason,
    }


def _signed_in(data: object) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    name = str(data.get("name") or "").strip()
    if not name:
        return None
    avatar = data.get("avatar")
    avatar_url = str(avatar).strip() if isinstance(avatar, str) else ""
    if avatar_url and not avatar_url.startswith(("https://", "http://")):
        avatar_url = ""
    try:
        points = max(0, int(data.get("points")))
    except (TypeError, ValueError):
        points = 0
    return {
        "signed_in": True,
        "register_url": REGISTER_URL,
        "name": name,
        "avatar": avatar_url or None,
        "points": points,
        "reason": None,
    }
