"""Executor 共用：模型输出 → tool 调用或 reply。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from core.modules.agent.core.code.conf.conf import PLACEHOLDER_REPLIES


def usable_reply(value: Any) -> str:
    reply = _strip_leaked_tool_json(str(value or ""))
    if not reply:
        return ""
    if reply in PLACEHOLDER_REPLIES:
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
