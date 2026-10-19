"""角色循环共用的模型 IO、决策解析与任务等待。"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from core.infra.ai import AiChannel
from core.infra.ai.contracts import AiError
from core.modules.agent.contracts import AgentError
from core.modules.agent.core.tools.strategy.read_reports import read_progress

_PRODUCT_PROVIDER = "ntq"
_WAIT_SECONDS = 45 * 60
_PLACEHOLDER_REPLIES = frozenset(
    {
        "给人看的话",
        "你的回答",
        "简明中文回答",
        "<简明中文回答>",
        "...",
        "…",
        "工具名",
    }
)
logger = logging.getLogger(__name__)


def ask(
    messages: List[Dict[str, str]],
    *,
    provider_id: str,
    max_tokens: int = 1024,
    timeout_seconds: Optional[float] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    ntq_mode: str = "",
    billing: Optional[Dict[str, Any]] = None,
) -> str:
    body = dict(extra_body or {})
    mode = str(ntq_mode or "").strip()
    if provider_id == _PRODUCT_PROVIDER and mode in {"ask", "work"}:
        body["ntq_mode"] = mode
    try:
        result = AiChannel.complete(
            messages,
            provider_id=provider_id,
            max_tokens=max_tokens,
            temperature=0.2,
            timeout_seconds=timeout_seconds,
            extra_body=body or None,
        )
    except AiError as exc:
        raise AgentError(str(exc)) from None
    accumulate_billing(billing, result.ntq if isinstance(result.ntq, dict) else None)
    return result.reply


def accumulate_billing(
    billing: Optional[Dict[str, Any]],
    ntq: Optional[Dict[str, Any]],
) -> None:
    if billing is None or not isinstance(ntq, dict):
        return
    try:
        spent = max(0.0, float(ntq.get("catfood_spent") or 0))
    except (TypeError, ValueError):
        spent = 0.0
    billing["catfood_spent"] = round(float(billing.get("catfood_spent") or 0) + spent, 2)
    for key in ("balance", "catfood"):
        if ntq.get(key) is None:
            continue
        try:
            billing["balance"] = round(max(0.0, float(ntq.get(key))), 2)
        except (TypeError, ValueError):
            pass


def await_task(result: Dict[str, Any]) -> Dict[str, Any]:
    """启动类工具先返回任务 id。等到结束，再把最终进度交给模型。"""
    task_id = str(result.get("task_id") or "").strip()
    deadline = time.monotonic() + _WAIT_SECONDS
    latest = dict(result)
    seen = ""
    while time.monotonic() < deadline:
        time.sleep(8)
        progress = read_progress({"task_id": task_id})
        latest = {**result, **progress}
        status = str(progress.get("status") or "")
        marker = f"{status} {progress.get('progress')} {progress.get('step')}"
        if marker != seen:
            seen = marker
            logger.info("任务 %s：%s", task_id, marker)
        if status in {"completed", "failed", "cancelled"}:
            if status == "completed" and progress.get("kind") != "scan":
                latest["note"] = "任务已结束。接着读执行报告，数字只能来自报告。"
            return latest
    latest["note"] = "等待超时，任务可能仍在跑。不要编写结果数字。"
    return latest


def usable_reply(value: Any) -> str:
    reply = _strip_leaked_tool_json(str(value or ""))
    if not reply:
        return ""
    if reply in _PLACEHOLDER_REPLIES:
        return ""
    if reply.startswith("<") and reply.endswith(">") and len(reply) < 40:
        return ""
    if '"tool"' in reply and '"arguments"' in reply:
        return ""
    return reply


def decision(text: str, tool_names: set[str]) -> Dict[str, Any]:
    raw = str(text or "").strip()
    for _start, _end, payload in iter_json_spans(raw):
        if not isinstance(payload, dict):
            continue
        tool = str(payload.get("tool") or payload.get("name") or "").strip()
        if not tool or tool in {"工具名", "<工具名>"}:
            continue
        arguments = payload.get("arguments")
        if arguments is None:
            arguments = {}
        if isinstance(arguments, dict):
            return {"tool": tool, "arguments": arguments}

    payload = json_object(raw)
    if isinstance(payload, dict):
        cleaned = usable_reply(payload.get("reply"))
        if cleaned:
            return {"reply": cleaned}
        named = _tool_name_before_json(raw, tool_names)
        if named:
            return {"tool": named, "arguments": payload}

    cleaned = usable_reply(raw)
    if cleaned and not cleaned.startswith("{"):
        return {"reply": cleaned}
    return {}


def json_object(text: str) -> Any:
    spans = iter_json_spans(text)
    return spans[0][2] if spans else None


def iter_json_spans(text: str) -> List[Tuple[int, int, Any]]:
    """按花括号平衡扫描 JSON 对象，返回 (start, end, obj)。"""
    body = _strip_code_fence(text)
    out: List[Tuple[int, int, Any]] = []
    index = 0
    length = len(body)
    while index < length:
        if body[index] != "{":
            index += 1
            continue
        depth = 0
        in_string = False
        escape = False
        end = -1
        for cursor in range(index, length):
            char = body[cursor]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = cursor
                    break
        if end < 0:
            break
        loaded = _loads_json_chunk(body[index : end + 1])
        if isinstance(loaded, dict):
            out.append((index, end, loaded))
        index = end + 1
    return out


def _strip_leaked_tool_json(text: str) -> str:
    body = _strip_code_fence(text)
    if not body:
        return ""
    keep: List[str] = []
    cursor = 0
    for start, end, payload in iter_json_spans(body):
        tool = ""
        if isinstance(payload, dict):
            tool = str(payload.get("tool") or payload.get("name") or "").strip()
        if tool:
            keep.append(body[cursor:start])
            cursor = end + 1
    keep.append(body[cursor:])
    cleaned = "".join(keep)
    return "\n".join(line for line in cleaned.splitlines() if line.strip()).strip()


def _tool_name_before_json(text: str, tool_names: set[str]) -> str:
    brace = text.find("{")
    head = text if brace < 0 else text[:brace]
    found = ""
    for line in head.splitlines():
        name = line.strip().strip("`").strip()
        if name in tool_names:
            found = name
    return found


def _strip_code_fence(text: str) -> str:
    body = str(text or "").strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:]
        body = body.strip()
    return body


def _loads_json_chunk(chunk: str) -> Any:
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        try:
            return json.loads(" ".join(chunk.splitlines()))
        except json.JSONDecodeError:
            return None
