"""投资建议陷阱：用本机 list_strategy_summaries 生成合规答复。"""

from __future__ import annotations

from typing import Any, Dict, List


def format_strategy_summaries_reply(result: Dict[str, Any]) -> str:
    """避免模型编造策略名；数字只来自工具结果。"""
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


def _pct_label(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) <= 1.5:
        return f"{number * 100:.2f}%"
    return f"{number:.2f}%"
