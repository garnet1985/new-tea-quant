"""荐股红线答复：用本机 list_strategy_summaries 生成合规研究摘要（不荐股）。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.agent.core.code.executor.shared.prompt_loader import load_reply


def format_strategy_summaries_reply(result: Dict[str, Any]) -> str:
    """避免模型编造策略名；数字只来自工具结果。

    展示：中文名优先；最多在括号里带 ``meta.key``；不展示路径 id / version id。
    """
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
        name = str(item.get("display_name") or key).strip() or key
        if not name:
            continue
        label = _strategy_label(name, key)
        if not item.get("has_report"):
            lines.append(f"- {label}：暂无资金层回测报告")
            continue
        summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
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
        if bits:
            lines.append(f"- {label}：{'，'.join(bits)}")
        else:
            lines.append(f"- {label}：有报告但摘要字段为空")
    lines.extend(["", load_reply("advice_foot")])
    return "\n".join(lines)


def _strategy_label(display_name: str, key: str) -> str:
    """展示名；仅当 key 有意义且与展示名不同时，在括号里附带 key。"""
    name = str(display_name or "").strip()
    meta = str(key or "").strip()
    if not name:
        return meta
    if not meta or meta == name:
        return name
    return f"{name}（{meta}）"


def _pct_label(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) <= 1.5:
        return f"{number * 100:.2f}%"
    return f"{number:.2f}%"
