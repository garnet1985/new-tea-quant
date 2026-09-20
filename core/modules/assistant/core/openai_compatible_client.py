"""OpenAI 兼容 chat/completions 客户端（实施层）。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from core.modules.assistant.contracts import AssistantError

_DEFAULT_TIMEOUT_SECONDS = 60.0
_DEFAULT_MAX_TOKENS = 2048
_USER_AGENT = "NTQ-assistant/0.1.0"


class OpenAICompatibleClient:
    """按 OpenAI Chat Completions 协议发一次非流式补全。"""

    def complete(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]],
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = 0.7,
    ) -> str:
        """发送 messages，返回助手文本。失败抛 ``AssistantError``（不含密钥）。"""
        url = _completions_url(base_url)
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
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
            with urllib.request.urlopen(request, timeout=float(timeout_seconds)) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise AssistantError(_message_from_http_error(exc)) from None
        except urllib.error.URLError as exc:
            raise AssistantError(f"无法连接供应商：{_short_reason(exc.reason)}") from None
        except TimeoutError:
            raise AssistantError("供应商请求超时") from None

        return _content_from_response(raw)


def _completions_url(base_url: str) -> str:
    return str(base_url or "").strip().rstrip("/") + "/chat/completions"


def _content_from_response(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise AssistantError("供应商返回无法解析") from None
    if not isinstance(data, dict):
        raise AssistantError("供应商返回无法解析")
    err = _message_from_error_payload(data)
    if err:
        raise AssistantError(err)
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AssistantError("供应商没有返回内容")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise AssistantError("供应商没有返回内容")
    return content


def _message_from_http_error(exc: urllib.error.HTTPError) -> str:
    raw = ""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        raw = ""
    parsed: Optional[Dict[str, Any]] = None
    if raw:
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            loaded = None
        if isinstance(loaded, dict):
            parsed = loaded
    if parsed:
        msg = _message_from_error_payload(parsed)
        if msg:
            return msg
    return f"供应商请求失败（HTTP {exc.code}）"


def _message_from_error_payload(data: Dict[str, Any]) -> str:
    err = data.get("error")
    if isinstance(err, dict):
        msg = str(err.get("message") or "").strip()
        if msg:
            return msg
    if isinstance(err, str) and err.strip():
        return err.strip()
    return ""


def _short_reason(reason: Any) -> str:
    text = str(reason or "").strip()
    if not text:
        return "网络错误"
    return text.split("\n", 1)[0][:200]
