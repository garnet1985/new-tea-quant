"""Present 阶段：scenario 清单命中 → 结论 + 模版再打模型改版式；否则透传。

也含模版加载（``content/templates/``）与工具结果里的短提醒。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.agent.core.code.conf.conf import (
    PRESENT_MAX_TOKENS,
    PRESENT_TIMEOUT_SECONDS,
    PRESENTATION_SCENARIOS,
    PRODUCT_PROVIDER_ID,
)
from core.modules.agent.core.code.executor.shared.complete import ask
from core.modules.agent.core.code.executor.shared.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# 用户话里「要呈现式总结」的弱信号（与 tools_seen 合取）
_PRICE_SUMMARY_RE = re.compile(
    r"(总结|解读|讲讲|讲清|分析|评语|成绩单|怎么样|如何看|帮我看|看看报告)"
)


def template_path(scenario: str) -> str:
    key = str(scenario or "").strip()
    path = PRESENTATION_SCENARIOS.get(key)
    if not path:
        raise KeyError(f"unknown presentation scenario: {key}")
    return path


def load_template(scenario: str) -> str:
    return load_prompt(template_path(scenario)).rstrip()


def template_tool_note(scenario: str, *, extra: str = "") -> str:
    """工具结果附带的短提醒（完整骨架在 present 阶段套用）。"""
    key = str(scenario or "").strip()
    bit = (
        f"呈现 scenario=`{key}`：工作结论写清数字与要点即可；"
        "最终版式由 present 阶段按模版输出。"
    )
    more = str(extra or "").strip()
    return f"{bit} {more}".strip() if more else bit


def known_scenarios() -> Mapping[str, str]:
    return dict(PRESENTATION_SCENARIOS)


def resolve_present_scenario(
    user_text: str,
    tools_seen: Sequence[Mapping[str, Any]] | None,
) -> Optional[str]:
    """按「场景清单」解析：命中则返回 scenario key，否则 None（透传）。"""
    if not PRESENTATION_SCENARIOS:
        return None
    # scenario: backtest_price — 读过价格层报告且用户要总结/解读
    if "backtest_price" in PRESENTATION_SCENARIOS and _match_backtest_price(
        user_text, tools_seen
    ):
        return "backtest_price"
    return None


def _match_backtest_price(
    user_text: str,
    tools_seen: Sequence[Mapping[str, Any]] | None,
) -> bool:
    if not _saw_ok_tool(tools_seen, "read_execution_report", layer="price"):
        return False
    return bool(_PRICE_SUMMARY_RE.search(str(user_text or "")))


def _saw_ok_tool(
    tools_seen: Sequence[Mapping[str, Any]] | None,
    tool: str,
    *,
    layer: str = "",
) -> bool:
    want = str(tool or "").strip()
    want_layer = str(layer or "").strip()
    for row in tools_seen or ():
        if not isinstance(row, Mapping):
            continue
        if str(row.get("tool") or "").strip() != want:
            continue
        if not row.get("ok"):
            continue
        if want_layer and str(row.get("layer") or "").strip() != want_layer:
            continue
        return True
    return False


def record_tool_seen(
    tools_seen: List[Dict[str, Any]],
    tool: str,
    result: Mapping[str, Any] | None,
) -> None:
    """work 循环里追加一条工具痕迹，供 present 解析 scenario。"""
    payload = result if isinstance(result, Mapping) else {}
    entry: Dict[str, Any] = {
        "tool": str(tool or "").strip(),
        "ok": bool(payload.get("ok")),
    }
    layer = str(payload.get("layer") or "").strip()
    if layer:
        entry["layer"] = layer
    tools_seen.append(entry)


def run_present(
    *,
    conclusion: str,
    scenario: Optional[str],
    provider_id: str,
    billing: Optional[Dict[str, Any]] = None,
) -> str:
    """有 scenario 且模版存在 → 打 present；否则原样返回 conclusion。"""
    text = str(conclusion or "").strip()
    if not text:
        return text
    key = str(scenario or "").strip()
    if not key or key not in PRESENTATION_SCENARIOS:
        return text
    try:
        template_path(key)
        template = load_template(key)
    except (KeyError, OSError, ValueError) as exc:
        logger.warning("present template missing for %s: %s", key, exc)
        return text
    if not template.strip():
        return text

    system = load_prompt("specific/present/system.md").rstrip()
    user = load_prompt(
        "specific/present/user.md",
        variables={
            "scenario": key,
            "template": template,
            "conclusion": text,
        },
    ).rstrip()
    try:
        formatted = ask(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            provider_id=provider_id,
            max_tokens=PRESENT_MAX_TOKENS,
            timeout_seconds=PRESENT_TIMEOUT_SECONDS,
            ntq_phase="act" if provider_id == PRODUCT_PROVIDER_ID else "",
            ntq_intent="present" if provider_id == PRODUCT_PROVIDER_ID else None,
            billing=billing,
        )
    except Exception:  # noqa: BLE001 — present 失败则透传结论
        logger.exception("present ask failed; falling back to conclusion")
        return text
    out = str(formatted or "").strip()
    return out or text
