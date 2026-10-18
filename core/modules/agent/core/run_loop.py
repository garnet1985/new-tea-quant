"""运行循环。经 Assistant.complete 走会员通道上的 glm-4-flash。

官网代理只转发文本，不转发 tools 字段。模型用一个 JSON 对象交出调用单，本机执行后再把摘要送回去。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.tool_catalog import ToolCatalog
from core.modules.agent.core.tool_runner import run_tool
from core.modules.assistant import Assistant
from core.modules.assistant.contracts import AssistantError

_MAX_STEPS = 6
_PROVIDER = "ntq"


class RunLoop:
    """模型点名与本机执行的循环。"""

    def __init__(self, catalog: ToolCatalog) -> None:
        self._catalog = catalog

    def run(self, content: str, *, max_steps: int = _MAX_STEPS) -> str:
        text = str(content or "").strip()
        if not text:
            raise AgentError("消息不能为空")
        steps = int(max_steps)
        if steps < 1 or steps > _MAX_STEPS:
            raise AgentError(f"一轮最多 {_MAX_STEPS} 次模型调用")
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _system_prompt(self._catalog)},
            {"role": "user", "content": text},
        ]
        for _ in range(steps):
            raw = _ask(messages)
            names = {
                spec.name for spec in self._catalog.list_tools() if spec.implemented
            }
            decision = _decision(raw, names)
            tool = decision.get("tool")
            if not tool:
                reply = str(decision.get("reply") or "").strip()
                if not reply:
                    raise AgentError("模型没有给出回复")
                return reply
            result = run_tool(self._catalog, str(tool), decision.get("arguments") or {})
            messages.append({"role": "assistant", "content": raw.strip()})
            messages.append(
                {
                    "role": "user",
                    "content": "工具结果：\n" + json.dumps(result, ensure_ascii=False),
                }
            )
        raise AgentError("这一轮调用次数已到上限，已停止")


def _ask(messages: List[Dict[str, str]]) -> str:
    try:
        result = Assistant.complete(
            messages,
            provider_id=_PROVIDER,
            max_tokens=2048,
            temperature=0.2,
        )
    except AssistantError as exc:
        raise AgentError(str(exc)) from None
    return result.reply


def _system_prompt(catalog: ToolCatalog) -> str:
    lines = [
        "你是 NTQ 的执行代理。根据用户需求和工具结果决定下一步。",
        "每次只输出一个 JSON 对象，不要 Markdown，不要解释。",
        '调用工具：{"tool":"工具名","arguments":{...}}',
        '直接回答用户：{"reply":"给人看的话"}',
        "只能使用下面列出的工具。数字必须来自工具结果，没有结果就不要写收益或次数。",
        "后台任务立刻返回任务 id。状态不是 completed 时先读进度，不要再启动一次。",
        "用户没有要求回测、归因或滚动对照时，不要调用 start_ 开头的工具。",
        "改进策略时一次只改敏感度最高的一个参数，改完要重新校验。",
        "",
        "工具：",
    ]
    for spec in catalog.list_tools():
        if not spec.implemented:
            continue
        params = _param_text(spec.parameters)
        lines.append(f"- {spec.name}：{spec.description} 参数：{params}")
    return "\n".join(lines)


def _param_text(schema: Dict[str, Any]) -> str:
    props = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(props, dict) or not props:
        return "无"
    required = set(schema.get("required") or [])
    bits = []
    for name, meta in props.items():
        desc = ""
        if isinstance(meta, dict):
            desc = str(meta.get("description") or "").strip()
        mark = "" if name in required else "，可省略"
        bits.append(f"{name}（{desc}{mark}）" if desc else f"{name}{mark}")
    return "；".join(bits)


def _decision(text: str, tool_names: set[str]) -> Dict[str, Any]:
    raw = str(text or "").strip()
    payload = _json_object(raw)
    if isinstance(payload, dict):
        tool = str(payload.get("tool") or payload.get("name") or "").strip()
        if tool:
            arguments = payload.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                return {"reply": raw}
            return {"tool": tool, "arguments": arguments}
        reply = payload.get("reply")
        if isinstance(reply, str) and reply.strip():
            return {"reply": reply.strip()}
        named = _tool_name_before_json(raw, tool_names)
        if named:
            return {"tool": named, "arguments": payload}
    if raw:
        return {"reply": raw}
    return {}


def _tool_name_before_json(text: str, tool_names: set[str]) -> str:
    head = text[: text.find("{")]
    found = ""
    for line in head.splitlines():
        name = line.strip().strip("`").strip()
        if name in tool_names:
            found = name
    return found


def _json_object(text: str) -> Any:
    body = text
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:]
        body = body.strip()
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(body[start : end + 1])
    except json.JSONDecodeError:
        return None
