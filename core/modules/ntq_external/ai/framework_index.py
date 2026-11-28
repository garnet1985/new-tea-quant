"""远端框架问题快速索引（可运营；失败可回落本机 wiki）。"""

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

_CACHE_TTL_SEC = 300.0
_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {"expires_at": 0.0, "payload": None}

_FIXTURE_ENV = "NTQ_FRAMEWORK_INDEX_FIXTURE"
_URL_ENV = "NTQ_FRAMEWORK_INDEX_URL"


def fetch_framework_index(*, force_refresh: bool = False) -> Dict[str, Any]:
    """拉取官网框架索引。无凭证时 ``ok=False, reason=missing_credential``。

    成功返回::
        {"ok": True, "version": str, "entries": list, "issued_at": str|None}
    """
    if os.environ.get(_FIXTURE_ENV, "").strip().lower() in {"1", "true", "yes"}:
        return _fixture_payload()

    token = member_token()
    if not token:
        return {
            "ok": False,
            "error": "缺少会员凭证",
            "reason": "missing_credential",
        }

    if not force_refresh:
        cached = _read_cache()
        if cached is not None:
            return cached

    url = str(os.environ.get(_URL_ENV) or "").strip() or (
        member_base_url().rstrip("/") + "/agent/framework-index"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
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
        return {
            "ok": False,
            "error": f"拉取框架索引失败（{type(exc).__name__}）",
            "reason": "fetch_failed",
        }

    normalized = normalize_framework_index_payload(data)
    if normalized.get("ok"):
        _write_cache(normalized)
    return normalized


def normalize_framework_index_payload(data: Any) -> Dict[str, Any]:
    """校验官网 JSON；需要 version + entries 列表。"""
    if not isinstance(data, dict):
        return {"ok": False, "error": "framework_index 响应不是对象"}
    version = str(data.get("version") or "").strip()
    entries = data.get("entries")
    if not version:
        return {"ok": False, "error": "framework_index 缺少 version"}
    if not isinstance(entries, list):
        return {"ok": False, "error": "framework_index 缺少 entries"}
    clean_entries = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        keywords = row.get("keywords")
        if isinstance(keywords, str):
            kw = [p.strip() for p in keywords.replace("，", ",").split(",") if p.strip()]
        elif isinstance(keywords, list):
            kw = [str(k).strip() for k in keywords if str(k).strip()]
        else:
            kw = []
        code = row.get("code")
        if isinstance(code, str):
            codes = [p.strip() for p in code.replace("\n", ";").split(";") if p.strip()]
        elif isinstance(code, list):
            codes = [str(p).strip() for p in code if str(p).strip()]
        else:
            codes = []
        clean_entries.append(
            {
                "id": str(row.get("id") or "").strip(),
                "title": title,
                "keywords": kw,
                "wiki": str(row.get("wiki") or "").strip(),
                "module": str(row.get("module") or "").strip(),
                "code": codes,
                "note": str(row.get("note") or "").strip(),
            }
        )
    return {
        "ok": True,
        "version": version,
        "issued_at": str(data.get("issued_at") or "").strip() or None,
        "entries": clean_entries,
    }


def clear_framework_index_cache() -> None:
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
    return normalize_framework_index_payload(
        {
            "version": "fixture-1",
            "issued_at": "fixture",
            "entries": [
                {
                    "id": "sharpe_calc",
                    "title": "资金层夏普怎么算",
                    "keywords": ["夏普", "sharpe", "怎么算", "如何计算"],
                    "wiki": "know_how/how_sharpe_is_calculated.md",
                    "module": "modules.strategy · portfolio",
                    "code": [
                        "core/modules/strategy/core/engines/portfolio/docs/DAILY_MTM_RISK_RATIOS.md",
                        "core/modules/strategy/core/engines/portfolio/report_manager/capital_metrics.py",
                    ],
                    "note": "fixture：日频盯市 ×√252",
                }
            ],
        }
    )
