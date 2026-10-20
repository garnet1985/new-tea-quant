"""干事者：工具循环写策略 / 跑回测。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.loop_runtime import ask, await_task, decision, usable_reply
from core.modules.agent.core.prompt_store import load_nudge
from core.modules.agent.core.roles.worker.prompt import worker_system_prompt
from core.modules.agent.core.session_store import update_state_from_tool
from core.modules.agent.core.tool_catalog import ToolCatalog
from core.modules.agent.core.tool_runner import run_tool

_WORK_EXTRA = {"thinking": {"type": "disabled"}}
_WORK_TIMEOUT = 120.0
_PRODUCT_PROVIDER = "ntq"
_OWN_WORK_PROVIDER = "deepseek"


def run(
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
        {"role": "system", "content": worker_system_prompt(catalog)},
        *memory,
        {"role": "user", "content": text},
    ]
    names = {spec.name for spec in catalog.list_tools() if spec.implemented}
    extra = dict(_WORK_EXTRA) if provider_id == _OWN_WORK_PROVIDER else {}
    zero_heal_active = False
    saw_rerun_after_zero = False
    for _ in range(max_steps):
        raw = ask(
            messages,
            provider_id=provider_id,
            max_tokens=4096,
            timeout_seconds=_WORK_TIMEOUT,
            extra_body=extra or None,
            ntq_phase="act" if provider_id == _PRODUCT_PROVIDER else "",
            ntq_intent="worker" if provider_id == _PRODUCT_PROVIDER else None,
            billing=billing,
        )
        chosen = decision(raw, names)
        tool = chosen.get("tool")
        if not tool:
            reply = usable_reply(chosen.get("reply"))
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
                asks_user_permission(reply) or is_deferred_plan_reply(reply)
            ):
                messages.append({"role": "assistant", "content": raw.strip() or "{}"})
                messages.append(
                    {"role": "user", "content": load_nudge("worker", "no_permission")}
                )
                continue
            if reply:
                return reply
            messages.append({"role": "assistant", "content": raw.strip() or "{}"})
            messages.append(
                {"role": "user", "content": load_nudge("worker", "empty_reply")}
            )
            continue
        result = run_tool(catalog, str(tool), chosen.get("arguments") or {})
        if result.get("task_id") and result.get("status") == "running":
            result = await_task(result)
        tool_name = str(tool)
        if zero_heal_active and tool_name.startswith("start_"):
            if str(result.get("status") or "") == "completed":
                saw_rerun_after_zero = True
        is_zero = is_zero_opportunity_report(tool_name, result)
        if is_zero and not saw_rerun_after_zero:
            zero_heal_active = True
            result = {**result, "note": _zero_opportunity_heal_nudge()}
        elif (
            zero_heal_active
            and saw_rerun_after_zero
            and tool_name in {"read_execution_report", "read_scan_report"}
            and result.get("ok")
        ):
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
    return load_nudge("worker", "zero_opportunity")


def asks_user_permission(reply: str) -> bool:
    return bool(
        re.search(
            r"(要我改|要不要改|要我帮你改|是否(?:要|需要)?改|要我重跑|要不要重跑|"
            r"要我继续|要不要继续|需要我改|方便我改吗|可以改吗|要我直接改)",
            str(reply or ""),
        )
    )


def is_deferred_plan_reply(reply: str) -> bool:
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


def is_zero_opportunity_report(tool_name: str, result: Dict[str, Any]) -> bool:
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
    if "total_opportunities" in summary:
        return _as_nonneg_int(summary.get("total_opportunities")) == 0
    return _as_nonneg_int(result.get("total_opportunities")) == 0


def _as_nonneg_int(value: Any) -> Optional[int]:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None
