"""运行循环。经 Assistant.complete 走会员通道上的 glm-4-flash。

官网代理只转发文本，不转发 tools 字段。模型用一个 JSON 对象交出调用单，本机执行后再把摘要送回去。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.tool_catalog import ToolCatalog
from core.modules.agent.core.tool_runner import run_tool
from core.modules.agent.core.tools.read_reports import read_progress
from core.modules.assistant import Assistant
from core.modules.assistant.contracts import AssistantError

_MAX_STEPS = 10
_WAIT_SECONDS = 45 * 60
logger = logging.getLogger(__name__)
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
            if result.get("task_id") and result.get("status") == "running":
                result = _await_task(result)
            messages.append({"role": "assistant", "content": raw.strip()})
            messages.append(
                {
                    "role": "user",
                    "content": "工具结果：\n" + json.dumps(result, ensure_ascii=False),
                }
            )
        raise AgentError("这一轮调用次数已到上限，已停止")


def _await_task(result: Dict[str, Any]) -> Dict[str, Any]:
    """启动类工具先返回任务 id。这里等到结束，再把最终进度交给模型。"""
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


def _ask(messages: List[Dict[str, str]]) -> str:
    try:
        result = Assistant.complete(
            messages,
            provider_id=_PROVIDER,
            max_tokens=4096,
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
        "启动类工具会等到结束再把结果给你。状态不是 completed 时不要编写收益，也不要再启动一次。",
        "用户没有要求回测、归因、滚动对照或扫描时，不要调用 start_ 开头的工具。",
        "用户要求扫描当前机会时调用 start_scan，结束后读 read_scan_report。不要编造没有列出的股票。",
        "用户要求改策略或写策略时：先 create_strategy，再 write_strategy_files，再 validate_strategy。",
        "校验未通过就按错误改文件，通过之前不要回测。",
        "回测结束后读 read_execution_report，资金结果用 layer=portfolio。",
        "止损和止盈的归因调用 start_attribute_price。资金层归因不排这两个参数。",
        "改进时只改敏感度最高的一个止损或止盈，不要改买卖信号，不要一次改两个。",
        "改完止盈止损后先 start_price_factor，再 start_portfolio，然后对比资金报告。",
        "目录已经存在时不要 create_strategy。",
        "strategy.py 里的函数必须原样使用这个签名，不要改参数名：",
        "def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:",
        "    rows = records.last(2)",
        '    prev = rows[0].get("macd_macdh_12_26_9_fast12_signal9_slow26")',
        '    curr = rows[1].get("macd_macdh_12_26_9_fast12_signal9_slow26")',
        "    不足两根，或 prev/curr 为 None，就返回 False。金叉是 prev <= 0 且 curr > 0。",
        "settings.py 必须以 settings = { 开头，是 Python 字典。不要写 YAML。布尔写 True / False。",
        "settings 顶层要有 is_enabled: True。meta.key 等于目录名。不要把 is_enabled 只放进 meta。",
        'data.base 为 {"data_key":"stock.kline.daily","indicators":{"macd":[{"fast":12,"slow":26,"signal":9}]}}。',
        "min_required_records 设为 60。simulation.execution 的 start_date 和 end_date 在用户没指定时用空字符串。",
        "必须保留 fees、goal、portfolio、scanner 这些块，不要只写 meta 和 data。",
        "校验失败时按 errors 修改，不要把同一份文件再写一遍。",
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
