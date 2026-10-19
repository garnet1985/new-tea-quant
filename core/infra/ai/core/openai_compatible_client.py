"""OpenAI 兼容 chat/completions 客户端（实施层）。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from core.infra.ai.contracts import AiError

_DEFAULT_TIMEOUT_SECONDS = 25.0
_DEFAULT_MAX_TOKENS = 2048
_USER_AGENT = "NTQ-ai/0.1.0"


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
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> str:
        text, _meta = self.complete_with_meta(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body=extra_body,
        )
        return text

    def complete_with_meta(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]],
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = 0.7,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        url = _completions_url(base_url)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }
        if isinstance(extra_body, dict):
            for key, value in extra_body.items():
                if key in {"model", "messages", "max_tokens", "temperature"}:
                    continue
                payload[key] = value
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
            with urllib.request.urlopen(
                request, timeout=float(timeout_seconds)
            ) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise AiError(_message_from_http_error(exc)) from None
        except urllib.error.URLError as exc:
            raise AiError(f"无法连接供应商：{_short_reason(exc.reason)}") from None
        except TimeoutError:
            raise AiError("供应商请求超时") from None

        return _content_and_meta_from_response(raw, fallback_model=model)


def _completions_url(base_url: str) -> str:
    return str(base_url or "").strip().rstrip("/") + "/chat/completions"


def _content_and_meta_from_response(
    raw: str, *, fallback_model: str
) -> Tuple[str, Dict[str, Any]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise AiError("供应商返回无法解析") from None
    if not isinstance(data, dict):
        raise AiError("供应商返回无法解析")
    err = _message_from_error_payload(data)
    if err:
        raise AiError(err)
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AiError("供应商没有返回内容")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise AiError("供应商没有返回内容")
    meta: Dict[str, Any] = {
        "model": str(data.get("model") or fallback_model or "").strip(),
    }
    if isinstance(data.get("ntq"), dict):
        meta["ntq"] = data.get("ntq")
    if isinstance(data.get("usage"), dict):
        meta["usage"] = data.get("usage")
    return content, meta


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
