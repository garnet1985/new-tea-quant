"""Derive beginner-facing insights from attribution ``report.json``."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


def build_insights(report: Dict[str, Any]) -> Dict[str, Any]:
    """Build conclusion-first insight payload for CLI / UI."""
    decision_space = report.get("decision_space") if isinstance(report.get("decision_space"), dict) else {}
    attribution = report.get("attribution") if isinstance(report.get("attribution"), dict) else {}
    classical = (
        attribution.get("classical") if isinstance(attribution.get("classical"), dict) else {}
    )
    univariate = (
        classical.get("univariate") if isinstance(classical.get("univariate"), dict) else {}
    )
    fields = univariate.get("fields") if isinstance(univariate.get("fields"), dict) else {}
    capture = decision_space.get("capture") if isinstance(decision_space.get("capture"), dict) else {}
    declared = (
        decision_space.get("declared_core")
        if isinstance(decision_space.get("declared_core"), dict)
        else {}
    )

    primary = _pick_primary_field(fields)
    if primary is None:
        return {
            "status": "empty",
            "headline": "这次没有可对比的变化条件，暂得不出结论。",
            "key_findings": [],
            "tiers": [],
            "explains": [],
            "does_not_explain": [
                "没有「会变化」的数字条件，无法做分档对比。",
            ],
            "next_steps": [
                "在策略命中时多记录几个会变化的现场条件（例如成交量、估值分位）。",
                "确认 capture 已开启，并重新跑一版枚举后再看归因。",
            ],
            "technical": _technical_shell(report, classical),
            "field_key": None,
        }

    key, field = primary
    buckets = _extract_buckets(field)
    tiers = _merge_to_natural_tiers(buckets)
    corr = field.get("correlation") if isinstance(field.get("correlation"), dict) else {}
    threshold = _constant_threshold_for(key, capture, declared)
    findings = _key_findings(key, tiers, corr)
    headline = _headline(key, tiers, corr)
    chart_note = _chart_note(key, field, tiers, threshold)

    return {
        "status": "ok",
        "field_key": key,
        "headline": headline,
        "chart_note": chart_note,
        "key_findings": findings,
        "tiers": tiers,
        "explains": _explains(key, tiers, corr, threshold),
        "does_not_explain": _does_not_explain(key, threshold, tiers),
        "next_steps": _next_steps(key, tiers, threshold, capture, fields),
        "technical": _technical_details(report, key, field, tiers, corr, classical),
    }


def _pick_primary_field(
    fields: Dict[str, Any],
) -> Optional[Tuple[str, Dict[str, Any]]]:
    best: Optional[Tuple[str, Dict[str, Any], float]] = None
    for key, field in fields.items():
        if not isinstance(field, dict):
            continue
        buckets = _extract_buckets(field)
        if len(buckets) < 2:
            continue
        corr = field.get("correlation") if isinstance(field.get("correlation"), dict) else {}
        rho = abs(float(corr.get("rho") or 0.0)) if corr.get("status") == "ok" else 0.0
        score = rho + (0.1 if buckets else 0.0)
        if best is None or score > best[2]:
            best = (str(key), field, score)
    if best is None:
        return None
    return best[0], best[1]


def _extract_buckets(field: Dict[str, Any]) -> List[Dict[str, Any]]:
    block = field.get("buckets") if isinstance(field.get("buckets"), dict) else {}
    if block.get("status") != "ok":
        return []
    rows = block.get("buckets") or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rng = row.get("range") if isinstance(row.get("range"), dict) else {}
        out.append(
            {
                "label": str(row.get("label") or row.get("bucket_id") or "?"),
                "min": _as_float(rng.get("min")),
                "max": _as_float(rng.get("max")),
                "count": int(row.get("count") or 0),
                "win_rate": _as_float(row.get("win_rate")),
                "mean_roi": _as_float(row.get("mean_roi")),
            }
        )
    return out


def _merge_to_natural_tiers(buckets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge ordered buckets into natural tiers by best binary separation."""
    if len(buckets) < 2:
        return list(buckets)
    if any(b.get("mean_roi") is None for b in buckets):
        return list(buckets)

    total = sum(int(b.get("count") or 0) for b in buckets)
    if total <= 0:
        return list(buckets)

    best_split = None
    best_diff = -1.0
    for index in range(len(buckets) - 1):
        left = list(buckets[: index + 1])
        right = list(buckets[index + 1 :])
        left_n = sum(int(b.get("count") or 0) for b in left)
        right_n = sum(int(b.get("count") or 0) for b in right)
        if left_n < max(30, total * 0.1) or right_n < max(30, total * 0.1):
            continue
        left_mean = _weighted_mean_roi(left)
        right_mean = _weighted_mean_roi(right)
        if left_mean is None or right_mean is None:
            continue
        diff = abs(left_mean - right_mean)
        if diff > best_diff:
            best_diff = diff
            best_split = index

    rois = [float(b["mean_roi"]) for b in buckets]
    span = max(rois) - min(rois)
    if best_split is None or span <= 1e-12 or best_diff < max(0.015, 0.30 * span):
        return list(buckets)

    left = list(buckets[: best_split + 1])
    right = list(buckets[best_split + 1 :])
    return [_merge_bucket_group(left, "低段"), _merge_bucket_group(right, "高段")]


def _weighted_mean_roi(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
    total = 0
    weighted = 0.0
    for row in rows:
        count = int(row.get("count") or 0)
        mean_roi = row.get("mean_roi")
        if count <= 0 or mean_roi is None:
            continue
        total += count
        weighted += float(mean_roi) * count
    if total <= 0:
        return None
    return weighted / total


def _merge_bucket_group(rows: Sequence[Dict[str, Any]], fallback_label: str) -> Dict[str, Any]:
    total = sum(int(r.get("count") or 0) for r in rows)
    win_count = 0.0
    roi_sum = 0.0
    mins = [r["min"] for r in rows if r.get("min") is not None]
    maxs = [r["max"] for r in rows if r.get("max") is not None]
    for row in rows:
        count = int(row.get("count") or 0)
        win_rate = row.get("win_rate")
        mean_roi = row.get("mean_roi")
        if win_rate is not None:
            win_count += float(win_rate) * count
        if mean_roi is not None:
            roi_sum += float(mean_roi) * count
    low = min(mins) if mins else None
    high = max(maxs) if maxs else None
    if low is not None and high is not None:
        label = f"{_fmt_num(low)}~{_fmt_num(high)}"
    else:
        label = fallback_label
    return {
        "label": label,
        "min": low,
        "max": high,
        "count": total,
        "win_rate": (win_count / total) if total else None,
        "mean_roi": (roi_sum / total) if total else None,
        "source_bucket_count": len(rows),
    }


def _key_findings(
    key: str,
    tiers: Sequence[Dict[str, Any]],
    corr: Dict[str, Any],
) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    if len(tiers) >= 2:
        best, worst = _best_worst_tiers(tiers)
        if best and worst and best.get("mean_roi") is not None and worst.get("mean_roi") is not None:
            best_roi = float(best["mean_roi"])
            worst_roi = float(worst["mean_roi"])
            if abs(worst_roi) > 1e-9:
                ratio = best_roi / worst_roi if worst_roi > 0 else None
            else:
                ratio = None
            if ratio is not None and ratio > 1.05:
                findings.append(
                    {
                        "value": f"{ratio:.1f}x",
                        "caption": (
                            f"「{key}」更好那一档的平均收益，"
                            f"大约是较差那一档的 {ratio:.1f} 倍"
                        ),
                    }
                )
            if best.get("win_rate") is not None and worst.get("win_rate") is not None:
                gap = abs(float(best["win_rate"]) - float(worst["win_rate"])) * 100
                findings.append(
                    {
                        "value": f"{gap:.0f}%",
                        "caption": (
                            f"胜率差距："
                            f"{float(best['win_rate']) * 100:.0f}% vs "
                            f"{float(worst['win_rate']) * 100:.0f}%"
                        ),
                    }
                )
        findings.append(
            {
                "value": f"{len(tiers)} 档",
                "caption": (
                    "实际有效分档数"
                    if len(tiers) < 5
                    else "按收益差距分成的档数"
                ),
            }
        )
    elif corr.get("status") == "ok" and corr.get("rho") is not None:
        rho = float(corr["rho"])
        findings.append(
            {
                "value": f"{rho:+.2f}",
                "caption": f"「{key}」与收益的相关方向（正=越高越好）",
            }
        )
    return findings


def _headline(key: str, tiers: Sequence[Dict[str, Any]], corr: Dict[str, Any]) -> str:
    if len(tiers) == 2:
        low, high = tiers[0], tiers[1]
        low_roi = low.get("mean_roi")
        high_roi = high.get("mean_roi")
        cut = high.get("min")
        if low_roi is not None and high_roi is not None and cut is not None:
            if float(low_roi) > float(high_roi):
                return (
                    f"「{key}」越低，赚得越多 — 但主要分成两档，"
                    f"不是无限越低越好（分水岭约 {_fmt_num(cut)}）"
                )
            return (
                f"「{key}」越高，赚得越多 — 但主要分成两档，"
                f"不是无限越高越好（分水岭约 {_fmt_num(cut)}）"
            )
    if len(tiers) > 2:
        best, _ = _best_worst_tiers(tiers)
        if best and best.get("min") is not None and best.get("max") is not None:
            return (
                f"「{key}」在 [{_fmt_num(best['min'])}, {_fmt_num(best['max'])}] "
                f"这一段表现最好"
            )
    if corr.get("status") == "ok" and corr.get("rho") is not None:
        rho = float(corr["rho"])
        if abs(rho) < 0.05:
            return f"「{key}」高低和赚亏关系很弱，这次看不出清晰规律。"
        if rho < 0:
            return f"「{key}」越高，这次样本里往往赚得越少。"
        return f"「{key}」越高，这次样本里往往赚得越多。"
    return f"已对「{key}」做了分档对比，请看下方证据。"


def _chart_note(
    key: str,
    field: Dict[str, Any],
    tiers: Sequence[Dict[str, Any]],
    threshold: Optional[float],
) -> str:
    n = field.get("n") or sum(int(t.get("count") or 0) for t in tiers)
    mins = [t["min"] for t in tiers if t.get("min") is not None]
    maxs = [t["max"] for t in tiers if t.get("max") is not None]
    parts = [f"{n} 笔机会"]
    if mins and maxs:
        parts.append(f"「{key}」落在 {_fmt_num(min(mins))} ~ {_fmt_num(max(maxs))}")
    if threshold is not None:
        parts.append(f"进场条件要求 {key} < {_fmt_num(threshold)}，所以看不到更高的区间")
    if len(tiers) == 2:
        parts.append(f"按收益落差自然分成 {len(tiers)} 档（不是机械五等分）")
    return " · ".join(parts)


def _explains(
    key: str,
    tiers: Sequence[Dict[str, Any]],
    corr: Dict[str, Any],
    threshold: Optional[float],
) -> List[str]:
    lines: List[str] = []
    if len(tiers) >= 2:
        best, worst = _best_worst_tiers(tiers)
        if best and worst and best.get("mean_roi") is not None and worst.get("mean_roi") is not None:
            if float(best["mean_roi"]) > float(worst["mean_roi"]):
                lines.append(
                    f"「{key}」落在更好那一档时，平均收益明显高于另一档。"
                )
        if len(tiers) == 2 and tiers[1].get("min") is not None:
            cut = tiers[1]["min"]
            low_better = (
                tiers[0].get("mean_roi") is not None
                and tiers[1].get("mean_roi") is not None
                and float(tiers[0]["mean_roi"]) > float(tiers[1]["mean_roi"])
            )
            if low_better:
                lines.append(
                    f"差距主要出现在「低于约 {_fmt_num(cut)}」和「更接近上限」之间，"
                    "中间没有平滑渐变。"
                )
                if threshold is not None and float(cut) < float(threshold):
                    lines.append(
                        f"值得试着把进场门槛从 {_fmt_num(threshold)} "
                        f"收到 {_fmt_num(cut)} 附近，再跑一版对比。"
                    )
    p_value = corr.get("p_value")
    if p_value is not None and float(p_value) < 0.05:
        lines.append("这种差距在这次样本里不太像纯巧合。")
    if not lines:
        lines.append("可以看到该条件与结果有一定共变，但规律还不够清晰。")
    return lines


def _does_not_explain(
    key: str,
    threshold: Optional[float],
    tiers: Sequence[Dict[str, Any]],
) -> List[str]:
    lines: List[str] = []
    if threshold is not None:
        lines.append(
            f"无法说明 {key} ≥ {_fmt_num(threshold)} 时怎样——策略根本不会在那些点进场。"
        )
    lines.append("换一段行情，这个分水岭未必还在同一位置。")
    if len(tiers) == 2 and tiers[1].get("min") is not None:
        cut = tiers[1]["min"]
        lines.append(
            f"「{_fmt_num(cut)}」是不是最优门槛，还需要改参数重跑对照，不能单凭这次就定死。"
        )
    else:
        lines.append("最优参数仍需改设置重跑验证，不能把相关当成因果。")
    return lines


def _next_steps(
    key: str,
    tiers: Sequence[Dict[str, Any]],
    threshold: Optional[float],
    capture: Dict[str, Any],
    fields: Dict[str, Any],
) -> List[str]:
    steps: List[str] = []
    if (
        len(tiers) == 2
        and threshold is not None
        and tiers[1].get("min") is not None
        and float(tiers[0].get("mean_roi") or 0) > float(tiers[1].get("mean_roi") or 0)
    ):
        cut = float(tiers[1]["min"])
        if cut < float(threshold):
            steps.append(
                f"把进场条件从 {key} < {_fmt_num(threshold)} 改成 "
                f"{key} < {_fmt_num(cut)}，重跑回测，看整体成绩是否更好。"
            )
    steps.append("换另一段市场环境再跑一遍，看分水岭是否还在附近。")
    varying_count = sum(
        1
        for summary in capture.values()
        if isinstance(summary, dict) and summary.get("role") == "varying"
    )
    if varying_count < 2 or len(fields) < 2:
        steps.append(
            "再加一个会变化的现场条件（例如成交量、估值分位），看能不能继续拉开差异。"
        )
    else:
        steps.append("结合多指标分析结果，看是否有第二个条件能继续筛选。")
    return steps[:3]


def _technical_shell(report: Dict[str, Any], classical: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sample_size": None,
        "range": None,
        "binning": None,
        "correlation": None,
        "disclaimer": str(classical.get("scope_note") or "").strip() or None,
        "strategy_key": report.get("strategy_key"),
        "step": report.get("step"),
        "version_id": report.get("version_id"),
    }


def _technical_details(
    report: Dict[str, Any],
    key: str,
    field: Dict[str, Any],
    tiers: Sequence[Dict[str, Any]],
    corr: Dict[str, Any],
    classical: Dict[str, Any],
) -> Dict[str, Any]:
    mins = [t["min"] for t in tiers if t.get("min") is not None]
    maxs = [t["max"] for t in tiers if t.get("max") is not None]
    binning = (
        f"按相邻档收益落差合并为 {len(tiers)} 档（原始分位桶再归并）"
        if len(tiers) < 5
        else "等频分位桶直接展示"
    )
    corr_text = None
    if corr.get("status") == "ok":
        corr_text = (
            f"Spearman ρ={_fmt_num(corr.get('rho'), 3)}"
            f"，p={_fmt_p(corr.get('p_value'))}"
        )
    return {
        "sample_size": field.get("n"),
        "field_key": key,
        "range": (
            f"[{_fmt_num(min(mins))}, {_fmt_num(max(maxs))}]" if mins and maxs else None
        ),
        "binning": binning,
        "correlation": corr_text,
        "disclaimer": (
            "本报告只描述这次回测里「已经触发」的机会内部差异，"
            "不构成因果证明或未来预测。"
        ),
        "strategy_key": report.get("strategy_key"),
        "step": report.get("step"),
        "version_id": report.get("version_id"),
        "classical_status": classical.get("status"),
    }


def _best_worst_tiers(
    tiers: Sequence[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    valid = [t for t in tiers if t.get("mean_roi") is not None]
    if not valid:
        return None, None
    best = max(valid, key=lambda item: float(item["mean_roi"]))
    worst = min(valid, key=lambda item: float(item["mean_roi"]))
    return best, worst


def _constant_threshold_for(
    key: str,
    capture: Dict[str, Any],
    declared: Dict[str, Any],
) -> Optional[float]:
    candidates = [
        f"{key}_oversold_threshold",
        f"{key}_threshold",
        "rsi_oversold_threshold",
    ]
    for name in candidates:
        for source in (declared, capture):
            entry = source.get(name)
            if not isinstance(entry, dict):
                continue
            if entry.get("role") in ("constant", "settings_knob", None):
                value = _as_float(entry.get("value"))
                if value is not None:
                    return value
    return None


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_num(value: Any, digits: int = 1) -> str:
    number = _as_float(value)
    if number is None:
        return "-"
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.{digits}f}"


def _fmt_p(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "-"
    if number < 0.001:
        return "< 0.001"
    return f"{number:.3f}"


__all__ = ["build_insights"]
