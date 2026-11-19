"""read_url：DeepSeek Fetch API（本机 deepseek 密钥）。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict
from urllib.parse import urlparse

from core.infra.ai import AiChannel
from core.modules.agent.core.code.conf.conf import (
    READ_URL_MAX_CHARS,
    WEB_SEARCH_PROVIDER_ID,
    WEB_SEARCH_TIMEOUT_SECONDS,
)

_FETCH_URL = "https://api.deepseek.com/v1/tools/fetch"
_USER_AGENT = "NTQ-agent-read-url/0.1.0"


def read_url(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """抓取单个 http(s) 页面为 Markdown 摘要。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"url", "max_chars"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    url = args.get("url")
    if not isinstance(url, str) or not url.strip():
        return {"ok": False, "error": "url 不能为空"}
    url = url.strip()
    if len(url) > 8192:
        return {"ok": False, "error": "url 过长"}
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"ok": False, "error": "url 须为 http(s) 且含主机名"}
    if parsed.username or parsed.password:
        return {"ok": False, "error": "url 不能含用户名或密码"}

    max_chars = args.get("max_chars", READ_URL_MAX_CHARS)
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        return {"ok": False, "error": "max_chars 须为正整数"}
    max_chars = min(max_chars, READ_URL_MAX_CHARS)

    api_key = AiChannel.load_api_key(WEB_SEARCH_PROVIDER_ID)
    if not api_key:
        return {
            "ok": False,
            "error": (
                f"阅读链接需要本机配置 {WEB_SEARCH_PROVIDER_ID} API Key"
                "（设置 → AI 助理）。"
            ),
        }

    body = json.dumps({"url": url}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        _FETCH_URL,
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
        with urllib.request.urlopen(
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
            "error": f"抓取服务 HTTP {exc.code}"
            + (f"：{detail}" if detail else ""),
        }
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"无法连接抓取服务：{exc.reason}"}
    except TimeoutError:
        return {"ok": False, "error": "抓取请求超时"}
    except Exception as exc:
        return {"ok": False, "error": f"抓取失败：{exc}"}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": "抓取响应无法解析"}
    if not isinstance(data, dict):
        return {"ok": False, "error": "抓取响应格式异常"}
    title = str(data.get("title") or "")
    content = str(data.get("content") or "")
    truncated = len(content) > max_chars
    return {
        "ok": True,
        "url": url,
        "title": title,
        "chars": min(len(content), max_chars),
        "truncated": truncated,
        "content": content[:max_chars],
        "note": "外网页内容仅作参考；禁止据此荐股或编造报价。",
    }
