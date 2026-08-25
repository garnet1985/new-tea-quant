"""User-facing scope notes and UI/CLI hints for attribution reports."""
from __future__ import annotations

from typing import Any, Dict, List

_SCOPE_NOTES: Dict[str, str] = {
    "enum": (
        "这份报告只回答：在这次机会枚举里，现场记录的条件（如 RSI）"
        "和交易结果（赚/亏）有没有一起变化。"
        "它不是因果证明，也不能用来预测下次一定怎样；"
        "也不重复总胜率、总收益这类整体成绩单。"
    ),
    "price": (
        "这份报告只回答：在这次价格模拟里，现场条件与成交结果/跳过原因"
        "有没有一起变化。不是因果证明，也不重复整体报表指标。"
    ),
    "portfolio": (
        "这份报告只回答：在这次组合模拟里，现场条件与成交/贡献"
        "有没有一起变化。部分细节若尚未齐备，相关分析可能暂缺。"
    ),
}


def build_scope_note(step: str) -> str:
    return _SCOPE_NOTES.get(str(step or "").strip(), _SCOPE_NOTES["enum"])


def build_hints_for_ui(
    *,
    step: str,
    decision_space: Dict[str, Any],
    attribution: Dict[str, Any],
) -> List[str]:
    hints: List[str] = []
    classical = attribution.get("classical") or {}
    classical_status = classical.get("status")
    capture = decision_space.get("capture") or {}
    declared = decision_space.get("declared_core") or {}

    if classical_status in ("ok", "partial"):
        hints.append("这里不重复「总胜率 / 总收益 / 净值曲线」——那些看整体成绩单即可。")

    constant_knobs = _constant_settings_knobs(declared, capture)
    run_comparison = classical.get("run_comparison") or {}
    run_comparison_ok = run_comparison.get("status") == "ok"
    for key in sorted(constant_knobs):
        value = (capture.get(key) or {}).get("value")
        if value is None:
            value = (declared.get(key) or {}).get("value")
        if run_comparison_ok:
            hints.append(
                f"参数「{key}」这次固定为 {value!r}；"
                "和对照版本的差别，见下方「两次回测对照」。"
            )
        else:
            hints.append(
                f"参数「{key}」这次固定为 {value!r}。"
                "想知道改它有没有用，需要换参数再跑一次，并做两次回测对照。"
            )

    for key, summary in sorted(capture.items()):
        if not isinstance(summary, dict):
            continue
        if summary.get("role") != "constant" or key in constant_knobs:
            continue
        hints.append(
            f"现场记录「{key}」这次始终相同，所以无法从本报告看出它好不好；"
            "需要对照另一次回测。"
        )

    multivariate = classical.get("multivariate") or {}
    if multivariate.get("status") == "skipped":
        reason = multivariate.get("reason")
        if reason == "insufficient_varying_fields":
            found = multivariate.get("found_features", 0)
            hints.append(
                f"「多指标一起看」需要至少 2 个会变化的数字条件（当前 {found} 个），"
                "所以这次只看了单个指标。"
            )
        elif reason == "insufficient_samples":
            hints.append("样本偏少，暂不做多指标分析；仍可先看分档结果。")

    if run_comparison.get("status") == "not_requested":
        hints.append(
            "还没指定对照版本。想比较「阈值 20 vs 25」这类差异，"
            "请带上 baseline 再跑归因。"
        )
    elif run_comparison.get("status") == "ok":
        comparison = run_comparison.get("comparison") or {}
        settings_diff = comparison.get("settings_diff") or []
        capture_diff = comparison.get("capture_diff") or []
        if settings_diff:
            keys = "、".join(str(item.get("key")) for item in settings_diff[:3])
            hints.append(
                f"两次回测的参数有差异（如 {keys}）。"
                "单个指标关系只解释各自那一次；参数本身好不好，要看两次结果差在哪。"
            )
        elif capture_diff:
            hints.append(
                "两次回测的现场条件分布不同；请结合对照结果理解变化来自哪里。"
            )
        elif not comparison.get("has_meaningful_diff"):
            hints.append(
                "和对照版本相比，现场条件几乎没变；"
                "若你预期不同，请确认版本号或参数是否已改过。"
            )

    univariate = classical.get("univariate") or {}
    fields = univariate.get("fields") or {}
    if step == "enum" and constant_knobs and fields:
        hints.append(
            "下面分档只描述「已经触发信号之后」机会内部的差别，"
            "不能据此判断「触发阈值本身」是不是最优。"
        )

    _append_significant_correlation_hint(hints, fields)

    if classical_status == "skipped":
        hints.append("这次没有可变化的数字条件，归因未展开。")

    ml = attribution.get("ml") or {}
    ml_status = ml.get("status")
    if ml_status in ("ok", "partial"):
        hints.append(
            "机器学习部分只解释「这一次」里更复杂的关系，不能外推到未来，也不能当因果。"
        )
        if ml_status == "partial":
            hints.append("细粒度解释未完全算出；仍可先看特征重要性排序。")
    elif ml_status == "skipped":
        reason = ml.get("reason")
        if reason == "insufficient_samples":
            required = ml.get("required_samples", 500)
            hints.append(f"样本不足（建议 ≥{required}），暂不做机器学习分析。")
        elif reason == "insufficient_varying_fields":
            hints.append("变化中的数字条件不足 2 个，暂不做机器学习分析。")

    return hints


def _constant_settings_knobs(
    declared: Dict[str, Any],
    capture: Dict[str, Any],
) -> List[str]:
    knobs: List[str] = []
    for key, entry in declared.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("role") != "settings_knob":
            continue
        capture_entry = capture.get(key) or {}
        if capture_entry.get("role") == "constant":
            knobs.append(str(key))
    return knobs


def _append_significant_correlation_hint(
    hints: List[str],
    fields: Dict[str, Any],
) -> None:
    for key, field in sorted(fields.items()):
        if not isinstance(field, dict):
            continue
        corr = field.get("correlation") or {}
        if corr.get("status") != "ok":
            continue
        p_value = corr.get("p_value")
        if p_value is None or p_value >= 0.05:
            continue
        rho = corr.get("rho")
        if rho is None:
            continue
        direction = "越高结果往往越好" if float(rho) > 0 else "越高结果往往越差"
        hints.append(
            f"「{key}」和结果在这次样本里同向变化较明显（{direction}）；"
            "换一段时间行情未必如此。"
        )
        return


__all__ = ["build_hints_for_ui", "build_scope_note"]
