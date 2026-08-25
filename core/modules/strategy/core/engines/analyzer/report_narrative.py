"""User-facing scope notes and UI hints for attribution reports."""
from __future__ import annotations

from typing import Any, Dict, List

_SCOPE_NOTES: Dict[str, str] = {
    "enum": (
        "解释本次 run、enum step 内 capture 与 outcome 如何共变；"
        "属 in-sample 描述，非因果证明、非未来预测，不重复 overall 胜率或净值。"
    ),
    "price": (
        "解释本次 run、price step 内 capture 与 roi / skip_reason 如何共变；"
        "属 in-sample 描述，非因果证明，不重复 overall 报表指标。"
    ),
    "portfolio": (
        "解释本次 run、portfolio step 内 capture 与成交/贡献如何共变；"
        "属 in-sample 描述，per-trade join 完成前部分 stage 可能 skipped。"
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
        hints.append("此处不重复 overall_report 的总胜率、总 ROI 或净值曲线。")

    constant_knobs = _constant_settings_knobs(declared, capture)
    run_comparison = classical.get("run_comparison") or {}
    run_comparison_ok = run_comparison.get("status") == "ok"
    for key in sorted(constant_knobs):
        value = (capture.get(key) or {}).get("value")
        if value is None:
            value = (declared.get(key) or {}).get("value")
        if run_comparison_ok:
            hints.append(
                f"旋钮 {key} 在本 run 内恒为 {value!r}；"
                "与 baseline 的差异见 run_comparison。"
            )
        else:
            hints.append(
                f"旋钮 {key} 在本 run 内恒为 {value!r}；"
                "调整该参数后请重跑并启用 run_comparison 对照 baseline version。"
            )

    for key, summary in sorted(capture.items()):
        if not isinstance(summary, dict):
            continue
        if summary.get("role") != "constant" or key in constant_knobs:
            continue
        hints.append(
            f"capture 字段 {key} 在本 run 内不变；"
            "univariate 无法解释其影响，需对照其它 version。"
        )

    multivariate = classical.get("multivariate") or {}
    if multivariate.get("status") == "skipped":
        reason = multivariate.get("reason")
        if reason == "insufficient_varying_fields":
            found = multivariate.get("found_features", 0)
            hints.append(
                f"多元归因需要至少 2 个 varying numeric capture（当前 {found} 个）；"
                "单变量结果仅描述各 field 独立关系。"
            )
        elif reason == "insufficient_samples":
            hints.append("样本量不足多元回归门槛；单变量分桶与相关仍可用于探索。")

    if run_comparison.get("status") == "not_requested":
        hints.append(
            "未指定 baseline version；对比两次 run（如不同阈值或 settings）需启用 run_comparison。"
        )
    elif run_comparison.get("status") == "ok":
        comparison = run_comparison.get("comparison") or {}
        settings_diff = comparison.get("settings_diff") or []
        capture_diff = comparison.get("capture_diff") or []
        if settings_diff:
            keys = ", ".join(str(item.get("key")) for item in settings_diff[:3])
            hints.append(
                f"run_comparison：settings 差异字段 {keys}；"
                "univariate 解释各自 run 内关系，阈值/旋钮效果请结合两次 run 的 outcome 差异理解。"
            )
        elif capture_diff:
            hints.append(
                "run_comparison：capture 分布或常量值有差异；"
                "请结合两次 run 的 decision_space 与 outcome 理解变化来源。"
            )
        elif not comparison.get("has_meaningful_diff"):
            hints.append(
                "run_comparison：当前与 baseline 的 decision_space 无显著差异；"
                "若预期不同，请确认 version 或 settings 是否已变更。"
            )

    univariate = classical.get("univariate") or {}
    fields = univariate.get("fields") or {}
    if step == "enum" and constant_knobs and fields:
        hints.append(
            "本 run 内 varying capture 仅描述「已通过筛选条件后的机会」内部差异，"
            "不能据此判断筛选阈值本身是否最优。"
        )

    _append_significant_correlation_hint(hints, fields)

    if classical_status == "skipped":
        reason = univariate.get("reason") or "no_varying_numeric_capture"
        hints.append(f"经典归因未运行：{reason}。")

    ml = attribution.get("ml") or {}
    ml_status = ml.get("status")
    if ml_status in ("ok", "partial"):
        hints.append(
            "ML 轨为 in-sample 拟合；XGB/SHAP 仅解释本次 run 内非线性关系，不可外推或作因果依据。"
        )
        if ml_status == "partial":
            shap_block = (ml.get("xgb") or {}).get("shap") or {}
            reason = shap_block.get("reason") or "unavailable"
            hints.append(f"SHAP 未完整产出（{reason}）；仍可参考 feature_importance.gain。")
    elif ml_status == "skipped":
        reason = ml.get("reason")
        if reason == "insufficient_samples":
            required = ml.get("required_samples", 500)
            hints.append(f"ML 轨 skipped：样本不足（需要 ≥{required}）。")
        elif reason == "insufficient_varying_fields":
            hints.append("ML 轨 skipped：需要至少 2 个 varying numeric capture。")

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
        hints.append(
            f"{key} 与 outcome 在本 run 内相关显著（Spearman ρ={float(rho):.3f}），"
            "仅说明样本内共变，换行情或样本未必成立。"
        )
        return


__all__ = ["build_hints_for_ui", "build_scope_note"]
