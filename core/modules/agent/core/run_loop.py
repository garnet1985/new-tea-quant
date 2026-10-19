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

# 含「机会数 0 → 改字段 → 重跑 → 再读报告」的自愈路径
_MAX_STEPS = 14
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
        "list_strategy_summaries",
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
# 门控勿凭会话旧数字直接答；建策/回测/质疑结果必须做事。
_FORCE_WORK_RE = re.compile(
    r"("
    r"(建|写|改|测|跑).{0,16}(策略|回测)|"
    r"回测|扫描|校验策略|归因|滚动|"
    r"缓存|复查|结果不对|不可能|没结果|没有机会|重跑|再跑|可行"
    r")",
    re.IGNORECASE,
)
# 「什么策略赚钱」类陷阱：不交给模型自由发挥，先读本机摘要再固定口径回复。
_ADVICE_TRAP_RE = re.compile(
    r"("
    r"什么策略.{0,12}(赚|挣)|"
    r"哪些策略.{0,12}(赚|挣)|"
    r"(能|会)?赚钱的策略|"
    r"推荐.{0,12}策略|"
    r"投资建议|"
    r"(该|应该)?买什么|"
    r"买什么股|"
    r"稳赚|"
    r"怎么赚钱|"
    r"哪(个|种)策略.{0,12}(赚|好|强)"
    r")",
    re.IGNORECASE,
)
_FABRICATED_STRATEGY_RE = re.compile(
    r"(策略\s*[A-Z]|Strategy\s*[A-Z]|策略[甲乙丙丁])",
    re.IGNORECASE,
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
    # 「什么策略赚钱」：强制读本机摘要，禁止模型编造「策略 A/B/C」。
    if _is_investment_advice_trap(text):
        result = run_tool(catalog, "list_strategy_summaries", {})
        update_state_from_tool(result, session_id)
        return {"reply": _format_strategy_summaries_reply(result)}
    # 建策/回测/质疑结果：禁止门控用会话旧 facts 直接 reply。
    if _FORCE_WORK_RE.search(str(text or "")):
        return {"handoff": True}

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
        if reply and _FABRICATED_STRATEGY_RE.search(reply):
            logger.warning("gate reply rejected for fabricated strategy labels")
            messages.append({"role": "assistant", "content": raw.strip() or "{}"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "上一条无效：禁止编造「策略 A/B/C」这类占位名。"
                        "请先调用 list_strategy_summaries，只用工具返回的真实 key 与数字回答；"
                        "没有报告就如实说暂无回测。"
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
    # 机会数为 0：拦住最终 reply，直到改代码并重跑后再读报告
    zero_heal_active = False
    saw_rerun_after_zero = False
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
            if reply and zero_heal_active and not saw_rerun_after_zero:
                messages.append({"role": "assistant", "content": raw.strip() or "{}"})
                messages.append(
                    {
                        "role": "user",
                        "content": _zero_opportunity_heal_nudge(),
                    }
                )
                continue
            if reply and (
                _asks_user_permission(reply) or _is_deferred_plan_reply(reply)
            ):
                messages.append({"role": "assistant", "content": raw.strip() or "{}"})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "不要只说计划或问许可。立刻调用 write_strategy_files 改文件，"
                            "再启动任务并读报告，最后用结论 reply。"
                        ),
                    }
                )
                continue
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
        tool_name = str(tool)
        if zero_heal_active and tool_name.startswith("start_"):
            if str(result.get("status") or "") == "completed":
                saw_rerun_after_zero = True
        is_zero = _is_zero_opportunity_report(tool_name, result)
        if is_zero and not saw_rerun_after_zero:
            # 首次（或重跑前）读到 0：拦住 reply，强制改字段再跑
            zero_heal_active = True
            result = {**result, "note": _zero_opportunity_heal_nudge()}
        elif (
            zero_heal_active
            and saw_rerun_after_zero
            and tool_name in {"read_execution_report", "read_scan_report"}
            and result.get("ok")
        ):
            # 已自查重跑并再读报告，允许交代（即使仍为 0）
            zero_heal_active = False
        update_state_from_tool(result, session_id)
        messages.append({"role": "assistant", "content": raw.strip()})
        messages.append(
            {
                "role": "user",
                "content": "工具结果：\n" + json.dumps(result, ensure_ascii=False),
            }
        )
    raise AgentError("这一轮调用次数已到上限，已停止")


def _zero_opportunity_heal_nudge() -> str:
    return (
        "机会数为 0：禁止现在向用户 reply，也不要问「要不要改」。"
        "立刻读 strategy.py 与 settings.py，核对 indicators 与 hooks 字段："
        "禁止 ma_ma20 这类臆造名；有 alias 只读 alias；无 alias 时 length=20 读 ma20；"
        "参数用 length 不用 window。"
        "改对后 validate_strategy，再 start 回测/扫描，再 read 报告，然后才能 reply。"
    )


def _asks_user_permission(reply: str) -> bool:
    """是否在向用户征求「要不要改」类许可。"""
    return bool(
        re.search(
            r"(要我改|要不要改|要我帮你改|是否(?:要|需要)?改|要我重跑|要不要重跑|"
            r"要我继续|要不要继续|需要我改|方便我改吗|可以改吗|要我直接改)",
            str(reply or ""),
        )
    )


def _is_deferred_plan_reply(reply: str) -> bool:
    """是否只报计划、尚未改文件/重跑（应继续做事）。"""
    text = str(reply or "")
    if re.search(
        r"(结论如下|敏感度|卡玛|夏普|总收益|机会总数|归因报告|group_id)",
        text,
    ):
        return False
    return bool(
        re.search(
            r"(我接下来会|下一步我会|下一步建议|这一步必须先|在真正跑出结果之前|"
            r"需要先把|必须先把|然后重跑|然后再读)",
            text,
        )
    )


def _is_zero_opportunity_report(tool_name: str, result: Dict[str, Any]) -> bool:
    """执行/扫描报告里机会或成交为 0 时需要强制自查。"""
    if not isinstance(result, dict) or not result.get("ok"):
        return False
    name = str(tool_name or "").strip()
    if name == "read_scan_report":
        return _as_nonneg_int(result.get("total_opportunities")) == 0
    if name != "read_execution_report":
        return False
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    layer = str(result.get("layer") or "").strip()
    if layer == "portfolio":
        return _as_nonneg_int(summary.get("total_trades")) == 0
    if layer == "price":
        return _as_nonneg_int(summary.get("total_investments")) == 0
    # enum 或未标 layer：看机会数
    if "total_opportunities" in summary:
        return _as_nonneg_int(summary.get("total_opportunities")) == 0
    return _as_nonneg_int(result.get("total_opportunities")) == 0


def _as_nonneg_int(value: Any) -> Optional[int]:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


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


def _is_investment_advice_trap(text: str) -> bool:
    raw = str(text or "").strip()
    return bool(raw and _ADVICE_TRAP_RE.search(raw))


def _has_brand_leak(text: str) -> bool:
    return bool(_BRAND_LEAK_RE.search(str(text or "")))


def _pct_label(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) <= 1.5:
        return f"{number * 100:.2f}%"
    return f"{number:.2f}%"


def _format_strategy_summaries_reply(result: Dict[str, Any]) -> str:
    """用本机 list_strategy_summaries 结果生成合规答复，避免模型编造策略名。"""
    head = (
        "NTQ 是研究与回测工具，不能提供投资建议，也不能告诉你「什么策略会赚钱」。\n\n"
        "下面是本机已有策略的历史回测摘要（资金层最新主版本；不代表未来）："
    )
    if not isinstance(result, dict) or not result.get("ok"):
        err = ""
        if isinstance(result, dict):
            err = str(result.get("error") or "").strip()
        detail = f"（{err}）" if err else ""
        return (
            "NTQ 是研究与回测工具，不能提供投资建议。\n\n"
            f"暂时无法读取本机策略列表{detail}。"
            "你可以先打开策略工作台查看已有策略，或自己写策略并回测验证。"
        )
    rows = result.get("strategies") if isinstance(result.get("strategies"), list) else []
    if not rows:
        return (
            "NTQ 是研究与回测工具，不能提供投资建议。\n\n"
            "本机目前还没有可列出的策略。"
            "我不能推荐「能赚钱」的策略；若要研究想法，请先创建策略并跑回测。"
        )
    lines: List[str] = [head, ""]
    for item in rows:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        name = str(item.get("display_name") or key).strip() or key
        label = key if name == key else f"{key}（{name}）"
        if not item.get("has_report"):
            lines.append(f"- `{label}`：暂无资金层回测报告")
            continue
        summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
        version = str(item.get("version_id") or "").strip()
        bits: List[str] = []
        if "total_return" in summary:
            bits.append(f"总收益 {_pct_label(summary.get('total_return'))}")
        if "max_drawdown" in summary:
            bits.append(f"最大回撤 {_pct_label(summary.get('max_drawdown'))}")
        if "win_rate" in summary:
            bits.append(f"胜率 {_pct_label(summary.get('win_rate'))}")
        if "sharpe_ratio" in summary:
            bits.append(f"夏普 {summary.get('sharpe_ratio')}")
        if "calmar_ratio" in summary:
            bits.append(f"卡玛 {summary.get('calmar_ratio')}")
        ver = f" v{version}" if version else ""
        if bits:
            lines.append(f"- `{label}`{ver}：{'，'.join(bits)}")
        else:
            lines.append(f"- `{label}`{ver}：有报告但摘要字段为空")
    lines.extend(
        [
            "",
            "这些数字只供研究对照，不是投资推荐。"
            "若要验证自己的想法，请在 NTQ 里编写策略并回测。",
        ]
    )
    return "\n".join(lines)


def _product_identity() -> List[str]:
    """门控 / 做事共用的产品身份，避免把「新茶」答成茶叶。"""
    return [
        "硬性事实（不可改写）：NTQ = New Tea Quant；中文名「新茶」。",
        "禁止把 NTQ 展开成 New Trading Question、New Trading Query 或任何其他英文。",
        "禁止把「新茶」解释成茶叶、茶饮、采摘或口感。",
        "身份：你是 New Tea Quant 桌面应用里的助理，对外自称「新茶」。",
        "简介要点：专注 A 股的量化策略回测框架，可写策略、回测、归因与扫描机会。",
        *_compliance_rules(),
    ]


def _compliance_rules() -> List[str]:
    """投资建议红线：门控与做事共用，防「什么策略赚钱」类陷阱。"""
    return [
        "红线：不提供投资建议；不预测涨跌；不回答「什么策略能赚钱」「该买哪只」「推荐策略」"
        "这类问题的推荐或承诺。",
        "用户若问能赚钱的策略/投资建议：先说明 NTQ 是研究与回测工具，不能给投资建议；"
        "然后二选一——用 list_strategy_summaries（必要时再读单策略报告）客观陈述本机历史回测数字，"
        "或委婉拒绝并引导用户用回测验证自己的想法。",
        "陈述回测时必须标明「历史回测 / 研究数据，不代表未来」；"
        "禁止把正收益说成「值得买」「会赚钱」「推荐用这个」。",
        "没有工具结果时禁止编造「所有策略」的收益、卡玛、夏普等数字。",
        "策略名必须用工具返回的真实 key（如 ma20_touch）；"
        "禁止「策略 A/B/C」、Strategy A 等占位名。",
    ]


def _gate_prompt(catalog: ToolCatalog) -> str:
    lines = [
        *_product_identity(),
        "你是 NTQ 的入口判断。只决定这一句是回答、读报告，还是交接去做复杂事。",
        "每次只输出一个 JSON 对象，不要 Markdown，不要解释，不要在 JSON 外写任何字。",
        '能直接回答时：{"reply":"<针对用户问题的真实中文回答>"}',
        "reply 必须是完整可用的回答内容；禁止照抄尖括号示例或任何占位词。",
        "reply 排版：指标与数字用短列表；结论/综合判断单独成段，不要写成列表最后一项。",
        "reply 里禁止再嵌套 tool 调用 JSON；要读报告就单独输出 tool 对象。",
        '读已有报告时只能用下面列出的只读工具：{"tool":"<工具名>","arguments":{...}}',
        "read_progress 必须带真实 task_id；没有 task_id 时不要调用，改为 handoff 或直接 reply。",
        '需要写策略、改代码、校验、回测、归因、滚动对照、扫描，或用户说结果不对/请复查/再检查时：{"handoff":"work"}',
        "不要编造收益或股票名单。数字只能来自工具结果。",
        "问「什么策略赚钱 / 投资建议」时：先 list_strategy_summaries，再用事实 reply；"
        "不要空口总结「所有策略」；也不要 handoff 去写新策略来「帮他赚钱」。",
        "会话状态里的旧 version_id / 机会数不能当新结论；用户要建策、回测或质疑结果时必须 handoff，不要直接 reply。",
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
        "每次只输出一个 JSON 对象，不要 Markdown，不要解释，不要在 JSON 外写任何字。",
        '调用工具：{"tool":"<工具名>","arguments":{...}}',
        '直接回答用户：{"reply":"<针对用户的真实中文回答>"}',
        "reply 必须是完整可用的回答；禁止照抄尖括号示例或占位词；禁止在 reply 里再写 tool JSON。",
        "硬性：能靠改文件继续推进的障碍，直接改、validate、重跑，再用结果 reply。",
        "禁止在 reply 里问「要我改吗」「要不要重跑」「是否继续」；用户要的是结论，不是许可。",
        "reply 排版：指标与数字用短列表；结论/综合判断单独成段，不要写成列表最后一项。",
        "只能使用下面列出的工具。数字必须来自工具结果，没有结果就不要写收益或次数。",
        "用户要「能赚钱的策略」时不要新建策略去迎合；先 list_strategy_summaries 或委婉拒绝。",
        "启动类工具会等到结束再把结果给你。状态不是 completed 时不要编写收益，也不要再启动一次。",
        "用户没有要求回测、归因、滚动对照或扫描时，不要调用 start_ 开头的工具。",
        "用户要求扫描当前机会时调用 start_scan，结束后读 read_scan_report。不要编造没有列出的股票。",
        "用户要求改策略或写策略时：先 create_strategy，再 write_strategy_files，再 validate_strategy。",
        "校验未通过就按错误改文件，通过之前不要回测。",
        "回测结束后先 read_execution_report layer=enum，再读 layer=portfolio 看资金。",
        "写均线策略时 settings 用 length（禁止 window）。推荐：",
        '{"ma":[{"length":20,"alias":"ma20"}]}，hooks 里只写 rows[i].get("ma20")。',
        "禁止臆造 ma_ma20、ma_window20；无 alias 时 length=20 的字段就是 ma20。",
        "MACD 用 alias：settings 写 alias=macd，hooks 读 macd_macdh_12_26_9。",
        "若枚举/扫描机会数为 0：禁止立刻 reply。先改字段、validate、重跑、再读报告后一次说清。",
        "归因 stop_loss 裸数字要求 settings.goal.stop_loss 已是单段 stages 结构；"
        "否则先 write_strategy_files 补上 "
        '{"goal":{"stop_loss":{"stages":[{"ratio":-0.1,"close_invest":True}]}}}，'
        "attribution 可用 attribution_py："
        '{"inputs":{"stop_loss":{"values":[-0.08,-0.1,-0.15]}},"cross":False}。'
        "改了 settings.goal 后须先 start_price_factor（或整段回测）再 start_attribute_price，"
        "读报告后 reply；禁止只陈述「接下来会改」而不调用工具。",
        "用户质疑结果或要求复查时，同样先读代码自查，不要空调用 read_progress。",
        "止损和止盈的归因调用 start_attribute_price。资金层归因不排这两个参数。",
        "改进时只改敏感度最高的一个止损或止盈，不要改买卖信号，不要一次改两个。",
        "改完止盈止损后先 start_price_factor，再 start_portfolio，然后对比资金报告。",
        "目录已经存在时不要 create_strategy。",
        "strategy.py 里的函数必须原样使用这个签名，不要改参数名：",
        "def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:",
        "    rows = records.last(2)",
        '    prev = rows[0].get("ma20")',
        '    curr = rows[1].get("ma20")',
        "    不足两根，或 prev/curr 为 None，就返回 False。",
        "settings.py 必须以 settings = { 开头，是 Python 字典。不要写 YAML。布尔写 True / False。",
        "settings 顶层要有 is_enabled: True。meta.key 等于目录名。不要把 is_enabled 只放进 meta。",
        'data.base 示例：{"data_key":"stock.kline.daily","indicators":{"ma":[{"length":20,"alias":"ma20"}]}}。',
        "indicators 的 alias 不参与计算；单列落盘名=alias，多列=alias_列名。同一 settings 里名字不可重复。",
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
    reply = _strip_leaked_tool_json(str(value or ""))
    if not reply:
        return ""
    if reply in _PLACEHOLDER_REPLIES:
        return ""
    # 尖括号包起来的 schema 示例
    if reply.startswith("<") and reply.endswith(">") and len(reply) < 40:
        return ""
    # 仍像工具调用的残留，勿展示
    if '"tool"' in reply and '"arguments"' in reply:
        return ""
    return reply


def _strip_leaked_tool_json(text: str) -> str:
    """去掉混在正文里的 tool JSON，避免把协议露给用户。"""
    body = _strip_code_fence(text)
    if not body:
        return ""
    keep: List[str] = []
    cursor = 0
    for start, end, payload in _iter_json_spans(body):
        tool = ""
        if isinstance(payload, dict):
            tool = str(payload.get("tool") or payload.get("name") or "").strip()
        if tool:
            keep.append(body[cursor:start])
            cursor = end + 1
    keep.append(body[cursor:])
    cleaned = "".join(keep)
    return "\n".join(line for line in cleaned.splitlines() if line.strip()).strip()


def _decision(text: str, tool_names: set[str]) -> Dict[str, Any]:
    raw = str(text or "").strip()
    # 优先从混排文本里捞第一个合法 tool（模型常先写一句道歉再贴 JSON）
    for _start, _end, payload in _iter_json_spans(raw):
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

    payload = _json_object(raw)
    if isinstance(payload, dict):
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


def _iter_json_spans(text: str) -> List[Tuple[int, int, Any]]:
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


def _json_object(text: str) -> Any:
    spans = _iter_json_spans(text)
    return spans[0][2] if spans else None
