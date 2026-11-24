"""web_search：优先 NTQ 远端 knowledge_brief；否则本机 deepseek Search。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from core.infra.ai import AiChannel
from core.infra.utils.core.net.ssl_context import urlopen_https
from core.modules.agent.core.code.conf.conf import (
    WEB_SEARCH_COUNT_DEFAULT,
    WEB_SEARCH_COUNT_MAX,
    WEB_SEARCH_PROVIDER_ID,
    WEB_SEARCH_TIMEOUT_SECONDS,
    WEB_SEARCH_URL,
)

_USER_AGENT = "NTQ-agent-web-search/0.1.0"


def web_search(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """按 query 搜索网页；返回简报/标题摘要/链接，不作荐股。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"query", "count"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "query 不能为空"}
    query = query.strip()
    if len(query) > 128:
        return {"ok": False, "error": "query 最多 128 个字符"}

    count = args.get("count", WEB_SEARCH_COUNT_DEFAULT)
    if isinstance(count, bool) or not isinstance(count, int):
        return {"ok": False, "error": "count 须为整数"}
    if count < 1 or count > WEB_SEARCH_COUNT_MAX:
        return {
            "ok": False,
            "error": f"count 须在 1～{WEB_SEARCH_COUNT_MAX}",
        }

    remote = _via_member_knowledge_brief(query, count)
    if remote is not None:
        return remote

    return _via_local_deepseek(query, count)


def _via_member_knowledge_brief(query: str, count: int) -> Optional[Dict[str, Any]]:
    """会员通道：一次远端 knowledge_brief（搜+总结）。无凭证则 None。"""
    try:
        from core.modules.ntq_external.ai import member_channel
    except ImportError:
        return None
    token = member_channel.member_token()
    if not token:
        return None
    base = member_channel.member_base_url().rstrip("/")
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": query}],
            "temperature": 0.2,
            "max_tokens": 1200,
            "ntq": {"phase": "act", "intent": "knowledge_brief"},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        headers={
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urlopen_https(
            request, timeout=float(WEB_SEARCH_TIMEOUT_SECONDS) + 25.0
        ) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:240]
        except Exception:
            detail = ""
        return {
            "ok": False,
            "via": "ntq",
            "error": f"远端知识简报 HTTP {exc.code}"
            + (f"：{detail}" if detail else ""),
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "via": "ntq",
            "error": f"无法连接远端知识简报：{exc.reason}",
        }
    except TimeoutError:
        return {"ok": False, "via": "ntq", "error": "远端知识简报超时"}
    except Exception as exc:
        return {"ok": False, "via": "ntq", "error": f"远端知识简报失败：{exc}"}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "via": "ntq", "error": "远端响应无法解析"}
    if not isinstance(data, dict):
        return {"ok": False, "via": "ntq", "error": "远端响应格式异常"}
    if isinstance(data.get("error"), dict):
        msg = str(data["error"].get("message") or data["error"])
        return {"ok": False, "via": "ntq", "error": msg}

    brief = ""
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict):
            brief = str(msg.get("content") or "").strip()
    ntq = data.get("ntq") if isinstance(data.get("ntq"), dict) else {}
    knowledge = ntq.get("knowledge") if isinstance(ntq.get("knowledge"), dict) else {}
    citations = knowledge.get("citations") if isinstance(knowledge.get("citations"), list) else []
    results: List[Dict[str, Any]] = []
    for item in citations[:count]:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": str(item.get("title") or ""),
                "url": str(item.get("url") or ""),
                "snippet": str(item.get("snippet") or ""),
                "summary": str(item.get("summary") or "")[:800],
            }
        )
    if not brief and not results:
        return {"ok": False, "via": "ntq", "error": "远端未返回简报"}
    return {
        "ok": True,
        "via": "ntq",
        "query": query,
        "brief": brief,
        "count": len(results),
        "results": results,
        "note": (
            "简报来自 NTQ 远端（已搜网并总结）。"
            "只作事实与背景参考；对用户可不强制贴链接；禁止据此荐股、预测涨跌或编造未出现的报价。"
        ),
    }


def _via_local_deepseek(query: str, count: int) -> Dict[str, Any]:
    api_key = AiChannel.load_api_key(WEB_SEARCH_PROVIDER_ID)
    if not api_key:
        return {
            "ok": False,
            "error": (
                "网页搜索需要会员通道（Provider=ntq 且已装载凭证），"
                f"或本机配置 {WEB_SEARCH_PROVIDER_ID} API Key（设置 → AI 助理）。"
            ),
        }

    payload = {
        "query": query,
        "count": count,
        "ori_question": query[:128],
        "need_content": False,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        WEB_SEARCH_URL,
        data=body,
        headers={
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen_https(
            request, timeout=float(WEB_SEARCH_TIMEOUT_SECONDS)
        ) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            detail = ""
        return {
            "ok": False,
            "via": "local_deepseek",
            "error": f"搜索服务 HTTP {exc.code}"
            + (f"：{detail}" if detail else ""),
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "via": "local_deepseek",
            "error": f"无法连接搜索服务：{exc.reason}",
        }
    except TimeoutError:
        return {"ok": False, "via": "local_deepseek", "error": "搜索请求超时"}
    except Exception as exc:
        return {"ok": False, "via": "local_deepseek", "error": f"搜索失败：{exc}"}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "via": "local_deepseek", "error": "搜索响应无法解析"}
    rows = data.get("results") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return {"ok": False, "via": "local_deepseek", "error": "搜索响应格式异常"}

    results: List[Dict[str, Any]] = []
    for item in rows[:count]:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": str(item.get("title") or ""),
                "url": str(item.get("url") or ""),
                "snippet": str(item.get("snippet") or ""),
                "summary": str(item.get("summary") or "")[:800],
                "site_name": item.get("site_name"),
                "date": item.get("date"),
                "authority": item.get("authority"),
                "rerank_score": item.get("rerank_score"),
            }
        )
    return {
        "ok": True,
        "via": "local_deepseek",
        "query": query,
        "count": len(results),
        "results": results,
        "note": (
            "只作事实与背景参考；对用户可不强制贴链接；禁止据此荐股、预测涨跌或编造未出现的报价。"
        ),
    }
