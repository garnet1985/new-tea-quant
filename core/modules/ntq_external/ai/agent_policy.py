"""Agent 产品准则：会员态必须拉取远端 policy；未登录为框架态。

产品形态（凭证判定 / 拉包 / 缓存 / mode）在本模块；agent 只消费门面结果。
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from core.infra.utils import Utils
from core.modules.ntq_external.ai.member_channel import member_base_url, member_token

# 短时缓存：仅加速重复 resolve；过期后必须重拉，失败不降级用旧包
_CACHE_TTL_SEC = 300.0
_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {"expires_at": 0.0, "payload": None}

_FIXTURE_ENV = "NTQ_AGENT_POLICY_FIXTURE"
_URL_ENV = "NTQ_AGENT_POLICY_URL"

_PRODUCT_FAIL_MSG = (
    "已登录会员，但无法从官网加载 NTQ Agent 产品准则。"
    "请检查网络后重试；产品模式下必须使用远端准则，不能继续对话。"
)


def resolve_agent_policy(*, force_refresh: bool = False) -> Dict[str, Any]:
    """对外门面：framework | product+sections | product+error。

    返回::
        {
          "mode": "framework" | "product",
          "ok": bool,
          "version": str | None,
          "sections": dict | None,
          "error": str | None,
          "reason": str | None,  # missing_credential | fetch_failed | None
        }
    """
    token = member_token()
    if not token:
        return {
            "mode": "framework",
            "ok": True,
            "version": None,
            "sections": None,
            "error": None,
            "reason": "missing_credential",
        }

    if not force_refresh:
        cached = _read_cache()
        if cached is not None:
            return cached

    fetched = fetch_agent_policy(token=token)
    if not fetched.get("ok"):
        return {
            "mode": "product",
            "ok": False,
            "version": None,
            "sections": None,
            "error": str(fetched.get("error") or _PRODUCT_FAIL_MSG),
            "reason": "fetch_failed",
        }

    payload = {
        "mode": "product",
        "ok": True,
        "version": fetched.get("version"),
        "sections": fetched.get("sections"),
        "error": None,
        "reason": None,
    }
    _write_cache(payload)
    return payload


def fetch_agent_policy(*, token: Optional[str] = None) -> Dict[str, Any]:
    """拉取并校验 policy 包。成功 ``ok=True`` 且含 ``sections``；失败 ``ok=False``。"""
    if os.environ.get(_FIXTURE_ENV, "").strip().lower() in {"1", "true", "yes"}:
        return _fixture_payload()

    bearer = str(token or member_token() or "").strip()
    if not bearer:
        return {"ok": False, "error": "缺少会员凭证"}

    url = str(os.environ.get(_URL_ENV) or "").strip() or (
        member_base_url().rstrip("/") + "/agent/policy"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
            "User-Agent": "NTQ-assistant/0.1.0",
        },
        method="GET",
    )
    try:
        with Utils.net.urlopen_https(request, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": f"{_PRODUCT_FAIL_MSG}（{type(exc).__name__}）"}

    normalized = normalize_policy_payload(data)
    if not normalized.get("ok"):
        return {
            "ok": False,
            "error": str(normalized.get("error") or _PRODUCT_FAIL_MSG),
        }
    return normalized


def normalize_policy_payload(data: Any) -> Dict[str, Any]:
    """校验官网 JSON；最小需要 version + sections.redlines。"""
    if not isinstance(data, dict):
        return {"ok": False, "error": "policy 响应不是对象"}
    version = str(data.get("version") or "").strip()
    sections = data.get("sections")
    if not version:
        return {"ok": False, "error": "policy 缺少 version"}
    if not isinstance(sections, dict):
        return {"ok": False, "error": "policy 缺少 sections"}
    redlines = str(sections.get("redlines") or "").strip()
    if not redlines:
        return {"ok": False, "error": "policy.sections.redlines 为空"}

    clean: Dict[str, Any] = {
        "redlines": redlines,
        "responsibility_can_do": str(sections.get("responsibility_can_do") or "").strip(),
        "responsibility_cannot_do": str(
            sections.get("responsibility_cannot_do") or ""
        ).strip(),
        "disclaimers": {},
        "replies": {},
    }
    disc = sections.get("disclaimers")
    if isinstance(disc, dict):
        clean["disclaimers"] = {
            str(k): str(v).strip()
            for k, v in disc.items()
            if str(v or "").strip()
        }
    replies = sections.get("replies")
    if isinstance(replies, dict):
        clean["replies"] = {
            str(k): str(v).strip()
            for k, v in replies.items()
            if str(v or "").strip()
        }

    return {
        "ok": True,
        "version": version,
        "issued_at": str(data.get("issued_at") or "").strip() or None,
        "sections": clean,
    }


def clear_agent_policy_cache() -> None:
    """测试用：清空短时缓存。"""
    with _cache_lock:
        _cache["expires_at"] = 0.0
        _cache["payload"] = None


def _read_cache() -> Optional[Dict[str, Any]]:
    with _cache_lock:
        payload = _cache.get("payload")
        if not isinstance(payload, dict):
            return None
        if float(_cache.get("expires_at") or 0) <= time.time():
            return None
        return dict(payload)


def _write_cache(payload: Dict[str, Any]) -> None:
    with _cache_lock:
        _cache["payload"] = dict(payload)
        _cache["expires_at"] = time.time() + _CACHE_TTL_SEC


def _fixture_payload() -> Dict[str, Any]:
    """开发/单测：不联网的权威包形状。"""
    return normalize_policy_payload(
        {
            "version": "fixture-1",
            "issued_at": "fixture",
            "sections": {
                "redlines": (
                    "硬性事实（不可改写）：NTQ = New Tea Quant；中文名「新茶」。\n"
                    "身份：你是 New Tea Quant 桌面应用里的助理，对外自称「新茶」。\n"
                    "红线：不荐股、不点名买卖标的、不预测涨跌、不承诺收益。"
                    "【远端产品准则 fixture】"
                ),
                "responsibility_can_do": (
                    "解答 NTQ 用法；协助策略与回测；提供研究向策略思路（须免责）；"
                    "网页搜索补充公开知识（不作荐股）。【远端】"
                ),
                "responsibility_cannot_do": (
                    "荐股、点名买卖标的、预测涨跌、承诺收益；充当实时行情终端。【远端】"
                ),
                "replies": {
                    "advice_head": (
                        "【远端准则】NTQ 是研究与回测工具，不能荐股，也不能告诉你该买哪一只。\n\n"
                        "下面是本机已有策略的历史回测摘要（不代表未来）："
                    ),
                    "advice_empty": (
                        "【远端准则】NTQ 不能荐股。本机暂无策略可列；"
                        "若要思路请直接说，不要问该买哪只。"
                    ),
                    "advice_foot": (
                        "【远端准则】这些数字只供研究对照，不是投资推荐。"
                    ),
                    "advice_list_unavailable": (
                        "【远端准则】NTQ 不能荐股。暂时无法读取本机策略列表{{detail}}。"
                    ),
                    "out_of_scope": (
                        "【远端准则】这不在新茶的服务范围内。"
                        "新茶不做实时行情报价或盘口查询。"
                    ),
                },
                "disclaimers": {
                    "specific": (
                        "以上仅为研究思路与工具辅助结果，不构成投资建议；"
                        "请自行验证，新茶不对结果负责。"
                    ),
                },
            },
        }
    )
