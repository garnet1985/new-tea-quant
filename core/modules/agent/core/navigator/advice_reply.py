"""投资建议陷阱：用本机 list_strategy_summaries 生成合规答复。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.agent.core.prompt_store import load_reply


def format_strategy_summaries_reply(result: Dict[str, Any]) -> str:
    """避免模型编造策略名；数字只来自工具结果。"""
    if not isinstance(result, dict) or not result.get("ok"):
        err = ""
        if isinstance(result, dict):
            err = str(result.get("error") or "").strip()
        detail = f"（{err}）" if err else ""
        return load_reply("advice_list_unavailable", variables={"detail": detail})
    rows = result.get("strategies") if isinstance(result.get("strategies"), list) else []
    if not rows:
        return load_reply("advice_empty")
    lines: List[str] = [load_reply("advice_head"), ""]
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
    lines.extend(["", load_reply("advice_foot")])
    return "\n".join(lines)


def _pct_label(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) <= 1.5:
        return f"{number * 100:.2f}%"
    return f"{number:.2f}%"
