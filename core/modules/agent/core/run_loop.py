"""运行循环。产品默认只走会员通道 ntq（auto）；本机拼 context 并执行工具。

官网代理只转发文本，不转发 tools 字段。模型用一个 JSON 对象交出调用单，本机执行后再把摘要送回去。
开发可用环境变量 NTQ_AGENT_OWN_KEYS=1 改走本机智谱门 + DeepSeek 做事（不扣猫粮）。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.session_store import (
    append_turn,
    context_block,
    default_session_id,
    recent_turns,
    update_state_from_tool,
)
from core.modules.agent.core.tool_catalog import ToolCatalog
from core.modules.agent.core.tool_runner import run_tool
from core.modules.agent.core.tools.strategy.read_reports import read_progress
from core.modules.assistant import Assistant
from core.modules.assistant.contracts import AssistantError

_MAX_STEPS = 10
_WAIT_SECONDS = 45 * 60
_PRODUCT_PROVIDER = "ntq"
_OWN_GATE_PROVIDER = "zhipu"
_OWN_WORK_PROVIDER = "deepseek"
_OWN_KEYS_ENV = "NTQ_AGENT_OWN_KEYS"
_WORK_EXTRA = {"thinking": {"type": "disabled"}}
_WORK_TIMEOUT = 120.0
_GATE_READ_TOOLS = frozenset(
    {
        "read_progress",
        "read_execution_report",
        "read_attribution_report",
        "read_scan_report",
    }
)
_GATE_MAX_STEPS = 4
# 模型偶发照抄 schema 示例；这些不能当作用户可见回复。
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
# 小模型常乱猜缩写 / 把「新茶」答成茶叶；身份问答直接用固定文案。
_PRODUCT_INTRO = (
    "NTQ 是 **New Tea Quant** 的缩写，中文名「新茶」。\n\n"
    "New Tea Quant（NTQ）是专注于 A 股的量化策略回测框架与桌面应用："
    "可编写策略、跑回测与归因、扫描交易机会。"
    "对话里的助理「新茶」就是这个产品的内置助手。\n\n"
    "主要特点：\n"
    "1. 回测拆成多步（枚举 → 价格因子 → 组合等），每步有独立报告，便于定位问题\n"
    "2. 策略与配置放在 userspace，框架升级不覆盖你的数据\n"
    "3. 支持策略开发、回测、归因与机会扫描\n"
    "4. 内置助理可解答用法、协助写策略与解读报告\n\n"
    "说明：这里的「新茶」是产品名，不是茶叶。"
    "NTQ 只展开为 New Tea Quant，不要猜成别的英文短语。"
)
_BRAND_LEAK_RE = re.compile(
    r"("
    r"new\s*trading\s*question|"
    r"new\s*trading\s*query|"
    r"new\s*tea\s*question|"
    r"新采摘|"
    r"采摘的茶|"
    r"茶叶|"
    r"茶饮|"
    r"春茶"
    r")",
    re.IGNORECASE,
)
_IDENTITY_BRAND_RE = re.compile(
    r"(新茶|ntq|new\s*tea(?:\s*quant)?)",
    re.IGNORECASE,
)
_IDENTITY_ASK_RE = re.compile(
    r"(是什么|什么意思|啥意思|缩写|全称|简介|介绍|特点|概述|干什么|做什么|谁)",
)
logger = logging.getLogger(__name__)


class RunLoop:
    """模型点名与本机执行的循环。"""

    def __init__(self, catalog: ToolCatalog) -> None:
        self._catalog = catalog

    def run(
        self,
        content: str,
        *,
        max_steps: int = _MAX_STEPS,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        text = str(content or "").strip()
        if not text:
            raise AgentError("消息不能为空")
        steps = int(max_steps)
        if steps < 1 or steps > _MAX_STEPS:
            raise AgentError(f"一轮最多 {_MAX_STEPS} 次模型调用")
        sid = str(session_id or "").strip() or default_session_id()
        memory = _memory_messages(sid)
        gate_provider, work_provider = _providers()
        billing: Dict[str, Any] = {"catfood_spent": 0.0, "balance": None}
        gate = _gate(
            self._catalog,
            text,
            memory=memory,
            provider_id=gate_provider,
            session_id=sid,
            ntq_mode="ask",
            billing=billing,
        )
        if not gate.get("handoff"):
            reply = str(gate.get("reply") or "").strip()
            if not reply:
                raise AgentError("模型没有给出回复")
            append_turn(
                user=text,
                reply=reply,
                channel=gate_provider,
                handoff=False,
                session_id=sid,
            )
            return _run_result(reply, handoff=False, billing=billing)

        reply = _work(
            self._catalog,
            text,
            memory=memory,
            max_steps=steps,
            session_id=sid,
            provider_id=work_provider,
            billing=billing,
        )
        append_turn(
            user=text,
            reply=reply,
            channel=work_provider,
            handoff=True,
            session_id=sid,
        )
        return _run_result(reply, handoff=True, billing=billing)


def _memory_messages(session_id: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    block = context_block(session_id)
    if block:
        messages.append(
            {
                "role": "system",
                "content": "以下是跨会话偏好和当前任务状态，回答时遵守：\n" + block,
            }
        )
    messages.extend(recent_turns(session_id))
    return messages


def _own_keys() -> bool:
    """开发用：显式打开后走本机供应商，不经会员通道。"""
    return os.environ.get(_OWN_KEYS_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _providers() -> Tuple[str, str]:
    """产品默认 ntq / ntq；自有密钥时门用智谱、做事用 DeepSeek。"""
    if _own_keys():
        return _OWN_GATE_PROVIDER, _OWN_WORK_PROVIDER
    return _PRODUCT_PROVIDER, _PRODUCT_PROVIDER


def _gate(
    catalog: ToolCatalog,
    text: str,
    *,
    memory: List[Dict[str, str]],
    provider_id: str,
    session_id: str,
    ntq_mode: str = "ask",
    billing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # 品牌/身份问答不交给小模型自由发挥，避免「New Trading Question」等穿帮。
    if _is_product_identity_question(text):
        return {"reply": _PRODUCT_INTRO}

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _gate_prompt(catalog)},
        *memory,
        {"role": "user", "content": text},
    ]
    for _ in range(_GATE_MAX_STEPS):
        raw = _ask(
            messages,
            provider_id=provider_id,
            ntq_mode=ntq_mode,
            billing=billing,
        )
        payload = _json_object(raw)
        if isinstance(payload, dict) and str(
            payload.get("handoff") or ""
        ).strip().lower() in {"work", "true", "1"}:
            return {"handoff": True}
        decision = _decision(raw, set(_GATE_READ_TOOLS))
        tool = str(decision.get("tool") or "").strip()
        if tool:
            if tool not in _GATE_READ_TOOLS:
                return {"handoff": True}
            result = run_tool(catalog, tool, decision.get("arguments") or {})
            update_state_from_tool(result, session_id)
            messages.append({"role": "assistant", "content": raw.strip()})
            messages.append(
                {
                    "role": "user",
                    "content": "工具结果：\n" + json.dumps(result, ensure_ascii=False),
                }
            )
            continue
        reply = _usable_reply(decision.get("reply"))
        if reply and _has_brand_leak(reply):
            logger.warning("gate reply rejected for brand leak")
            messages.append({"role": "assistant", "content": raw.strip() or "{}"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "上一条穿帮了：NTQ 只能是 New Tea Quant（新茶），"
                        "不是 New Trading Question，也不是茶叶。"
                        "请按产品事实重答，"
                        '只输出 {"reply":"..."}。'
                    ),
                }
            )
            continue
        if reply:
            return {"reply": reply}
        # 空回复 / 示例占位：再问一轮，不要把占位文案展示给用户。
        messages.append({"role": "assistant", "content": raw.strip() or "{}"})
        messages.append(
            {
                "role": "user",
                "content": (
                    "上一条无效：reply 不能为空，也不能是示例占位。"
                    "请针对用户原问题给出真实中文回答，"
                    '只输出 {"reply":"..."}。'
                ),
            }
        )
        continue
    return {"handoff": True}


def _work(
    catalog: ToolCatalog,
    text: str,
    *,
    memory: List[Dict[str, str]],
    max_steps: int,
    session_id: str,
    provider_id: str,
    billing: Optional[Dict[str, Any]] = None,
) -> str:
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _system_prompt(catalog)},
        *memory,
        {"role": "user", "content": text},
    ]
    names = {spec.name for spec in catalog.list_tools() if spec.implemented}
    extra = dict(_WORK_EXTRA) if provider_id == _OWN_WORK_PROVIDER else {}
    ntq_mode = "work" if provider_id == _PRODUCT_PROVIDER else ""
    for _ in range(max_steps):
        raw = _ask(
            messages,
            provider_id=provider_id,
            max_tokens=4096,
            timeout_seconds=_WORK_TIMEOUT,
            extra_body=extra or None,
            ntq_mode=ntq_mode,
            billing=billing,
        )
        decision = _decision(raw, names)
        tool = decision.get("tool")
        if not tool:
            reply = _usable_reply(decision.get("reply"))
            if reply:
                return reply
            messages.append({"role": "assistant", "content": raw.strip() or "{}"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "上一条无效：reply 不能为空或示例占位。"
                        "请根据工具结果用中文回答用户，"
                        '只输出 {"reply":"..."}。'
                    ),
                }
            )
            continue
        result = run_tool(catalog, str(tool), decision.get("arguments") or {})
        if result.get("task_id") and result.get("status") == "running":
            result = _await_task(result)
        update_state_from_tool(result, session_id)
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


def _ask(
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
        result = Assistant.complete(
            messages,
            provider_id=provider_id,
            max_tokens=max_tokens,
            temperature=0.2,
            timeout_seconds=timeout_seconds,
            extra_body=body or None,
        )
    except AssistantError as exc:
        raise AgentError(str(exc)) from None
    _accumulate_billing(billing, result.ntq if isinstance(result.ntq, dict) else None)
    return result.reply


def _accumulate_billing(
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


def _run_result(
    reply: str,
    *,
    handoff: bool,
    billing: Dict[str, Any],
) -> Dict[str, Any]:
    spent = billing.get("catfood_spent")
    try:
        catfood_spent = round(max(0.0, float(spent or 0)), 2)
    except (TypeError, ValueError):
        catfood_spent = 0.0
    balance = billing.get("balance")
    try:
        balance_out = None if balance is None else round(max(0.0, float(balance)), 2)
    except (TypeError, ValueError):
        balance_out = None
    return {
        "reply": str(reply or ""),
        "handoff": bool(handoff),
        "mode": "work" if handoff else "ask",
        "catfood_spent": catfood_spent,
        "balance": balance_out,
    }


def _is_product_identity_question(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw or not _IDENTITY_BRAND_RE.search(raw):
        return False
    if _IDENTITY_ASK_RE.search(raw):
        return True
    # 「NTQ？」这类极短追问也视为身份问答
    return len(raw) <= 24


def _has_brand_leak(text: str) -> bool:
    return bool(_BRAND_LEAK_RE.search(str(text or "")))


def _product_identity() -> List[str]:
    """门控 / 做事共用的产品身份，避免把「新茶」答成茶叶。"""
    return [
        "硬性事实（不可改写）：NTQ = New Tea Quant；中文名「新茶」。",
        "禁止把 NTQ 展开成 New Trading Question、New Trading Query 或任何其他英文。",
        "禁止把「新茶」解释成茶叶、茶饮、采摘或口感。",
        "身份：你是 New Tea Quant 桌面应用里的助理，对外自称「新茶」。",
        "简介要点：专注 A 股的量化策略回测框架，可写策略、回测、归因与扫描机会。",
    ]


def _gate_prompt(catalog: ToolCatalog) -> str:
    lines = [
        *_product_identity(),
        "你是 NTQ 的入口判断。只决定这一句是回答、读报告，还是交接去做复杂事。",
        "每次只输出一个 JSON 对象，不要 Markdown，不要解释。",
        '能直接回答时：{"reply":"<针对用户问题的真实中文回答>"}',
        "reply 必须是完整可用的回答内容；禁止照抄尖括号示例或任何占位词。",
        '读已有报告时只能用下面列出的只读工具：{"tool":"<工具名>","arguments":{...}}',
        '需要写策略、改代码、校验、回测、归因、滚动对照或扫描时：{"handoff":"work"}',
        "不要编造收益或股票名单。数字只能来自工具结果。",
        "用户说「继续」「改一下」且当前任务状态里已有待确认的做事意图时，用 handoff。",
        "",
        "只读工具：",
    ]
    for spec in catalog.list_tools():
        if spec.name not in _GATE_READ_TOOLS or not spec.implemented:
            continue
        lines.append(
            f"- {spec.name}：{spec.description} 参数：{_param_text(spec.parameters)}"
        )
    return "\n".join(lines)


def _system_prompt(catalog: ToolCatalog) -> str:
    lines = [
        *_product_identity(),
        "你是 NTQ 的执行代理。根据用户需求和工具结果决定下一步。",
        "每次只输出一个 JSON 对象，不要 Markdown，不要解释。",
        '调用工具：{"tool":"<工具名>","arguments":{...}}',
        '直接回答用户：{"reply":"<针对用户的真实中文回答>"}',
        "reply 必须是完整可用的回答；禁止照抄尖括号示例或占位词。",
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
        '    prev = rows[0].get("macd_macdh_12_26_9")',
        '    curr = rows[1].get("macd_macdh_12_26_9")',
        "    不足两根，或 prev/curr 为 None，就返回 False。金叉是 prev <= 0 且 curr > 0。",
        "settings.py 必须以 settings = { 开头，是 Python 字典。不要写 YAML。布尔写 True / False。",
        "settings 顶层要有 is_enabled: True。meta.key 等于目录名。不要把 is_enabled 只放进 meta。",
        'data.base 为 {"data_key":"stock.kline.daily","indicators":{"macd":[{"fast":12,"slow":26,"signal":9,"alias":"macd"}]}}。',
        "indicators 可写 alias：单列落盘名用 alias；多列（如 MACD）为 alias_列名。同一 settings 里 alias 与默认名不可重复。",
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


def _usable_reply(value: Any) -> str:
    reply = str(value or "").strip()
    if not reply:
        return ""
    if reply in _PLACEHOLDER_REPLIES:
        return ""
    # 尖括号包起来的 schema 示例
    if reply.startswith("<") and reply.endswith(">") and len(reply) < 40:
        return ""
    return reply


def _decision(text: str, tool_names: set[str]) -> Dict[str, Any]:
    raw = str(text or "").strip()
    payload = _json_object(raw)
    if isinstance(payload, dict):
        tool = str(payload.get("tool") or payload.get("name") or "").strip()
        if tool and tool not in {"工具名", "<工具名>"}:
            arguments = payload.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                cleaned = _usable_reply(raw)
                return {"reply": cleaned} if cleaned else {}
            return {"tool": tool, "arguments": arguments}
        cleaned = _usable_reply(payload.get("reply"))
        if cleaned:
            return {"reply": cleaned}
        named = _tool_name_before_json(raw, tool_names)
        if named:
            return {"tool": named, "arguments": payload}
    cleaned = _usable_reply(raw)
    if cleaned and not cleaned.startswith("{"):
        return {"reply": cleaned}
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
    candidate = body[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # 模型常在 JSON 字符串里直接换行，压成空格后再试一次
        try:
            return json.loads(" ".join(candidate.splitlines()))
        except json.JSONDecodeError:
            return None
