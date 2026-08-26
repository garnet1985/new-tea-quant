"""Derive beginner-facing insights from attribution ``report.json``."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


class InsightBuilder:
    @classmethod
    def build(cls, report: Dict[str, Any]) -> Dict[str, Any]:
        """Build conclusion-first insight payload for CLI / UI."""
        step = str(report.get("step") or "enum").strip() or "enum"
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
        skip_summary = (
            classical.get("skip_summary")
            if isinstance(classical.get("skip_summary"), dict)
            else {}
        )
        primary = cls._pick_primary_field(fields)
        run_comparison = cls._run_comparison_insights(classical)
        if primary is None:
            empty_findings: List[Dict[str, str]] = []
            skipped = int(skip_summary.get("skipped_count") or 0)
            total = int(skip_summary.get("investment_count") or 0)
            if skipped > 0 and total > 0:
                empty_findings.append(
                    {
                        "value": f"{skipped}",
                        "caption": f"价格层有 {skipped}/{total} 笔因规则被跳过（未进收益分档）",
                    }
                )
            next_steps = [
                "在策略命中时多记录几个会变化的现场条件（例如成交量、估值分位）。",
                f"确认 capture 已开启，并重新跑{cls._step_rerun_label(step)}后再看归因。",
            ]
            next_steps = cls._merge_next_steps(next_steps, run_comparison.get("next_steps") or [])
            headline = "这次没有可对比的变化条件，暂得不出结论。"
            if run_comparison.get("status") == "ok" and run_comparison.get("headline"):
                headline = str(run_comparison["headline"])
            return {
                "status": "empty" if run_comparison.get("status") != "ok" else "ok",
                "headline": headline,
                "key_findings": empty_findings,
                "tiers": [],
                "explains": [],
                "does_not_explain": [
                    "没有「会变化」的数字条件，无法做分档对比。",
                ],
                "next_steps": next_steps,
                "technical": cls._technical_shell(report, classical, skip_summary=skip_summary),
                "field_key": None,
                "other_fields": [],
                "run_comparison": run_comparison,
                "multivariate": cls._multivariate_insights(classical),
                "ml": cls._ml_insights(attribution),
            }
        key, field = primary
        buckets = cls._extract_buckets(field)
        tiers = cls._merge_to_natural_tiers(buckets)
        corr = field.get("correlation") if isinstance(field.get("correlation"), dict) else {}
        threshold = cls._constant_threshold_for(key, capture, declared)
        findings = cls._key_findings(key, tiers, corr, skip_summary=skip_summary)
        headline = cls._headline(key, tiers, corr)
        chart_note = cls._chart_note(key, field, tiers, threshold, step=step)
        other_fields = cls._other_field_insights(fields, primary_key=key)
        multivariate = cls._multivariate_insights(classical)
        ml = cls._ml_insights(attribution)
        next_steps = cls._merge_next_steps(
            cls._next_steps(key, tiers, threshold, capture, fields),
            list(run_comparison.get("next_steps") or [])
            + list(multivariate.get("next_steps") or [])
            + list(ml.get("next_steps") or []),
        )
        return {
            "status": "ok",
            "field_key": key,
            "headline": headline,
            "chart_note": chart_note,
            "key_findings": findings,
            "tiers": tiers,
            "other_fields": other_fields,
            "explains": cls._explains(key, tiers, corr, threshold),
            "does_not_explain": cls._does_not_explain(key, threshold, tiers),
            "next_steps": next_steps,
            "technical": cls._technical_details(
                report, key, field, tiers, corr, classical, skip_summary=skip_summary
            ),
            "run_comparison": run_comparison,
            "multivariate": multivariate,
            "ml": ml,
        }
    @staticmethod
    def _pick_primary_field(
        fields: Dict[str, Any],
) -> Optional[Tuple[str, Dict[str, Any]]]:
        best: Optional[Tuple[str, Dict[str, Any], float]] = None
        for key, field in fields.items():
            if not isinstance(field, dict):
                continue
            buckets = InsightBuilder._extract_buckets(field)
            corr = field.get("correlation") if isinstance(field.get("correlation"), dict) else {}
            corr_ok = corr.get("status") == "ok" and corr.get("rho") is not None
            if len(buckets) < 2 and not corr_ok:
                continue
            rho = abs(float(corr.get("rho") or 0.0)) if corr_ok else 0.0
            score = rho + (0.5 if len(buckets) >= 2 else 0.0) + (
                0.05 if int(field.get("n") or 0) >= 2 else 0.0
            )
            if best is None or score > best[2]:
                best = (str(key), field, score)
        if best is None:
            return None
        return best[0], best[1]
    @staticmethod
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
                    "min": InsightBuilder._as_float(rng.get("min")),
                    "max": InsightBuilder._as_float(rng.get("max")),
                    "count": int(row.get("count") or 0),
                    "win_rate": InsightBuilder._as_float(row.get("win_rate")),
                    "mean_roi": InsightBuilder._as_float(row.get("mean_roi")),
                }
            )
        return out
    @staticmethod
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
            left_mean = InsightBuilder._weighted_mean_roi(left)
            right_mean = InsightBuilder._weighted_mean_roi(right)
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
        return [InsightBuilder._merge_bucket_group(left, "低段"), InsightBuilder._merge_bucket_group(right, "高段")]
    @staticmethod
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
    @staticmethod
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
            label = f"{InsightBuilder._fmt_num(low)}~{InsightBuilder._fmt_num(high)}"
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
    @staticmethod
    def _key_findings(
        key: str,
        tiers: Sequence[Dict[str, Any]],
        corr: Dict[str, Any],
        *,
        skip_summary: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
        findings: List[Dict[str, str]] = []
        if len(tiers) >= 2:
            best, worst = InsightBuilder._best_worst_tiers(tiers)
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
        skipped = int((skip_summary or {}).get("skipped_count") or 0)
        total = int((skip_summary or {}).get("investment_count") or 0)
        if skipped > 0 and total > 0:
            findings.append(
                {
                    "value": f"{skipped}",
                    "caption": f"价格层有 {skipped}/{total} 笔因规则被跳过（未进收益分档）",
                }
            )
        return findings
    @staticmethod
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
                        f"不是无限越低越好（分水岭约 {InsightBuilder._fmt_num(cut)}）"
                    )
                return (
                    f"「{key}」越高，赚得越多 — 但主要分成两档，"
                    f"不是无限越高越好（分水岭约 {InsightBuilder._fmt_num(cut)}）"
                )
        if len(tiers) > 2:
            best, _ = InsightBuilder._best_worst_tiers(tiers)
            if best and best.get("min") is not None and best.get("max") is not None:
                return (
                    f"「{key}」在 [{InsightBuilder._fmt_num(best['min'])}, {InsightBuilder._fmt_num(best['max'])}] "
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
    @staticmethod
    def _chart_note(
        key: str,
        field: Dict[str, Any],
        tiers: Sequence[Dict[str, Any]],
        threshold: Optional[float],
        *,
        step: str = "enum",
) -> str:
        n = field.get("n") or sum(int(t.get("count") or 0) for t in tiers)
        mins = [t["min"] for t in tiers if t.get("min") is not None]
        maxs = [t["max"] for t in tiers if t.get("max") is not None]
        unit = "笔机会"
        if step == "price":
            unit = "笔价格成交"
        elif step == "portfolio":
            unit = "笔组合成交"
        parts = [f"{n} {unit}"]
        if mins and maxs:
            parts.append(f"「{key}」落在 {InsightBuilder._fmt_num(min(mins))} ~ {InsightBuilder._fmt_num(max(maxs))}")
        if threshold is not None:
            parts.append(f"进场条件要求 {key} < {InsightBuilder._fmt_num(threshold)}，所以看不到更高的区间")
        buckets_meta = field.get("buckets") if isinstance(field.get("buckets"), dict) else {}
        if buckets_meta.get("status") == "skipped":
            reason = buckets_meta.get("reason")
            if reason == "insufficient_samples":
                parts.append("样本偏少，暂不做分档柱图，先看相关方向")
            else:
                parts.append("这次未能分档，先看相关方向")
        elif len(tiers) == 2:
            parts.append(f"按收益落差自然分成 {len(tiers)} 档（不是机械五等分）")
        return " · ".join(parts)
    @staticmethod
    def _explains(
        key: str,
        tiers: Sequence[Dict[str, Any]],
        corr: Dict[str, Any],
        threshold: Optional[float],
) -> List[str]:
        lines: List[str] = []
        if len(tiers) >= 2:
            best, worst = InsightBuilder._best_worst_tiers(tiers)
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
                        f"差距主要出现在「低于约 {InsightBuilder._fmt_num(cut)}」和「更接近上限」之间，"
                        "中间没有平滑渐变。"
                    )
                    if threshold is not None and float(cut) < float(threshold):
                        lines.append(
                            f"值得试着把进场门槛从 {InsightBuilder._fmt_num(threshold)} "
                            f"收到 {InsightBuilder._fmt_num(cut)} 附近，再跑一版对比。"
                        )
        p_value = corr.get("p_value")
        if p_value is not None and float(p_value) < 0.05:
            lines.append("这种差距在这次样本里不太像纯巧合。")
        if not lines and corr.get("status") == "ok" and corr.get("rho") is not None:
            rho = float(corr["rho"])
            if abs(rho) < 0.15:
                lines.append("相关很弱，只能说这次几乎看不出单向规律。")
            else:
                lines.append("暂时只能看到相关方向；样本不足以做稳定分档。")
        if not lines:
            lines.append("可以看到该条件与结果有一定共变，但规律还不够清晰。")
        return lines
    @staticmethod
    def _does_not_explain(
        key: str,
        threshold: Optional[float],
        tiers: Sequence[Dict[str, Any]],
) -> List[str]:
        lines: List[str] = []
        if threshold is not None:
            lines.append(
                f"无法说明 {key} ≥ {InsightBuilder._fmt_num(threshold)} 时怎样——策略根本不会在那些点进场。"
            )
        if len(tiers) >= 2:
            lines.append("换一段行情，这个分水岭未必还在同一位置。")
            if len(tiers) == 2 and tiers[1].get("min") is not None:
                cut = tiers[1]["min"]
                lines.append(
                    f"「{InsightBuilder._fmt_num(cut)}」是不是最优门槛，还需要改参数重跑对照，不能单凭这次就定死。"
                )
            else:
                lines.append("最优参数仍需改设置重跑验证，不能把相关当成因果。")
        else:
            lines.append("样本不足以做稳定分档，相关方向也可能随行情变化。")
            lines.append("这不是因果证明，也不能直接当改参依据。")
        return lines
    @staticmethod
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
                    f"把进场条件从 {key} < {InsightBuilder._fmt_num(threshold)} 改成 "
                    f"{key} < {InsightBuilder._fmt_num(cut)}，重跑回测，看整体成绩是否更好。"
                )
        if len(tiers) >= 2:
            steps.append("换另一段市场环境再跑一遍，看分水岭是否还在附近。")
        else:
            steps.append("积累更多成交样本后再看分档，样本太少时分档不稳定。")
            steps.append("换另一段市场环境再跑一遍，看相关方向是否还在。")
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
    @staticmethod
    def _technical_shell(
        report: Dict[str, Any],
        classical: Dict[str, Any],
        *,
        skip_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "sample_size": None,
            "range": None,
            "binning": None,
            "correlation": None,
            "disclaimer": str(classical.get("scope_note") or "").strip() or None,
            "strategy_key": report.get("strategy_key"),
            "step": report.get("step"),
            "version_id": report.get("version_id"),
        }
        skipped = int((skip_summary or {}).get("skipped_count") or 0)
        if skipped > 0:
            by_reason = (skip_summary or {}).get("by_reason") or {}
            reason_text = "、".join(
                f"{name}×{count}" for name, count in list(by_reason.items())[:3]
            )
            out["skip_summary"] = (
                f"跳过 {skipped} 笔"
                + (f"（{reason_text}）" if reason_text else "")
            )
        return out
    @staticmethod
    def _technical_details(
        report: Dict[str, Any],
        key: str,
        field: Dict[str, Any],
        tiers: Sequence[Dict[str, Any]],
        corr: Dict[str, Any],
        classical: Dict[str, Any],
        *,
        skip_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
        mins = [t["min"] for t in tiers if t.get("min") is not None]
        maxs = [t["max"] for t in tiers if t.get("max") is not None]
        if not tiers:
            binning = "样本不足，未做分档（仅相关方向）"
        elif len(tiers) < 5:
            binning = f"按相邻档收益落差合并为 {len(tiers)} 档（原始分位桶再归并）"
        else:
            binning = "等频分位桶直接展示"
        corr_text = None
        if corr.get("status") == "ok":
            corr_text = (
                f"Spearman ρ={InsightBuilder._fmt_num(corr.get('rho'), 3)}"
                f"，p={InsightBuilder._fmt_p(corr.get('p_value'))}"
            )
        step = str(report.get("step") or "enum")
        unit = "已触发机会"
        if step == "price":
            unit = "价格成交"
        elif step == "portfolio":
            unit = "组合成交"
        out: Dict[str, Any] = {
            "sample_size": field.get("n"),
            "field_key": key,
            "range": (
                f"[{InsightBuilder._fmt_num(min(mins))}, {InsightBuilder._fmt_num(max(maxs))}]" if mins and maxs else None
            ),
            "binning": binning,
            "correlation": corr_text,
            "disclaimer": (
                f"本报告只描述这次回测里「{unit}」内部差异，"
                "不构成因果证明或未来预测。"
            ),
            "strategy_key": report.get("strategy_key"),
            "step": report.get("step"),
            "version_id": report.get("version_id"),
            "classical_status": classical.get("status"),
        }
        skipped = int((skip_summary or {}).get("skipped_count") or 0)
        if skipped > 0:
            by_reason = (skip_summary or {}).get("by_reason") or {}
            reason_text = "、".join(
                f"{name}×{count}" for name, count in list(by_reason.items())[:3]
            )
            out["skip_summary"] = (
                f"跳过 {skipped} 笔"
                + (f"（{reason_text}）" if reason_text else "")
            )
        return out
    @staticmethod
    def _step_rerun_label(step: str) -> str:
        mapping = {
            "enum": "一版机会枚举",
            "price": "一版价格模拟",
            "portfolio": "一版组合模拟",
        }
        return mapping.get(step, "这一层")
    @staticmethod
    def _best_worst_tiers(
        tiers: Sequence[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        valid = [t for t in tiers if t.get("mean_roi") is not None]
        if not valid:
            return None, None
        best = max(valid, key=lambda item: float(item["mean_roi"]))
        worst = min(valid, key=lambda item: float(item["mean_roi"]))
        return best, worst
    @staticmethod
    def _constant_threshold_for(
        key: str,
        capture: Dict[str, Any],
        declared: Dict[str, Any],
) -> Optional[float]:
        """Upper-bound style entry caps (e.g. RSI oversold). Do not guess floors."""
        candidates = [f"{key}_oversold_threshold", f"max_{key}", f"{key}_max"]
        if key == "rsi":
            candidates.append("rsi_oversold_threshold")
        for name in candidates:
            for source in (declared, capture):
                entry = source.get(name)
                if not isinstance(entry, dict):
                    continue
                if entry.get("role") in ("constant", "settings_knob", None):
                    value = InsightBuilder._as_float(entry.get("value"))
                    if value is not None:
                        return value
        return None
    @staticmethod
    def _other_field_insights(
        fields: Dict[str, Any],
        *,
        primary_key: Optional[str],
) -> List[Dict[str, str]]:
        """One-liners for secondary varying fields (not the primary headline)."""
        ranked: List[Tuple[float, str, Dict[str, Any]]] = []
        for key, field in fields.items():
            if not isinstance(field, dict) or key == primary_key:
                continue
            corr = field.get("correlation") if isinstance(field.get("correlation"), dict) else {}
            if corr.get("status") != "ok" or corr.get("rho") is None:
                continue
            ranked.append((abs(float(corr["rho"])), str(key), field))
        ranked.sort(key=lambda item: item[0], reverse=True)
        out: List[Dict[str, str]] = []
        for _, key, field in ranked[:4]:
            corr = field.get("correlation") or {}
            rho = float(corr["rho"])
            if abs(rho) < 0.05:
                detail = "和赚亏关系很弱"
            elif rho < 0:
                detail = "越高往往赚得越少"
            else:
                detail = "越高往往赚得越多"
            out.append(
                {
                    "key": key,
                    "value": f"{rho:+.2f}",
                    "caption": f"「{key}」{detail}",
                }
            )
        return out
    @staticmethod
    def _multivariate_insights(classical: Dict[str, Any]) -> Dict[str, Any]:
        block = (
            classical.get("multivariate")
            if isinstance(classical.get("multivariate"), dict)
            else {}
        )
        status = str(block.get("status") or "skipped")
        if status in ("ok", "partial"):
            ranking = InsightBuilder._rank_multivariate_features(block)
            top = ranking[0] if ranking else None
            headline = "多个条件一起看时，能分出相对更重要的信号。"
            if top:
                headline = (
                    f"多指标一起看时，「{top['key']}」对结果影响相对最大"
                    f"（{top['caption']}）"
                )
            return {
                "status": status,
                "headline": headline,
                "features": list(block.get("features") or []),
                "found_features": len(block.get("features") or []),
                "n": block.get("n"),
                "ranking": ranking,
                "explains": [
                    "下面排序只解释「这一次」里谁更重要，不是因果排名。",
                ],
                "does_not_explain": [
                    "不能据此删掉其他条件；换行情排序可能变。",
                ],
                "next_steps": [
                    "先盯住排名靠前的条件，单独收紧/放宽后再对照回测。",
                ],
            }
        reason = str(block.get("reason") or "")
        found = block.get("found_features")
        if found is None and block.get("features"):
            found = len(block.get("features") or [])
        required = block.get("required_features") or block.get("required_samples")
        n = block.get("n")
        if reason == "insufficient_varying_fields":
            headline = (
                f"变化中的数字条件不足 {required} 个"
                f"（当前 {found if found is not None else 0} 个），暂不能多指标一起看。"
            )
            next_steps = ["再 capture 至少 2 个会变化的数字条件，然后重跑归因。"]
        elif reason in ("insufficient_samples", "insufficient_aligned_samples"):
            headline = (
                f"已有多个变化条件，但样本只有 {n} 笔"
                f"（建议 ≥{required}），暂不做多指标回归。"
            )
            next_steps = ["积累更多成交/机会后再跑，或先看上面的单指标分档。"]
        else:
            headline = "这次没做多指标一起看。"
            next_steps = []
        return {
            "status": "skipped",
            "headline": headline,
            "reason": reason,
            "found_features": found,
            "features": list(block.get("features") or []),
            "n": n,
            "ranking": [],
            "explains": [],
            "does_not_explain": [],
            "next_steps": next_steps,
        }
    @staticmethod
    def _ml_insights(attribution: Dict[str, Any]) -> Dict[str, Any]:
        block = attribution.get("ml") if isinstance(attribution.get("ml"), dict) else {}
        status = str(block.get("status") or "skipped")
        xgb = block.get("xgb") if isinstance(block.get("xgb"), dict) else {}
        if status in ("ok", "partial") and xgb.get("status") in ("ok", "partial"):
            importance = xgb.get("feature_importance") or []
            top = importance[0] if importance and isinstance(importance[0], dict) else None
            headline = "机器学习也给出了特征重要性排序（仅解释本次）。"
            ranking: List[Dict[str, str]] = []
            for item in importance[:4]:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("feature") or "?")
                score = item.get("importance")
                ranking.append(
                    {
                        "key": name,
                        "value": InsightBuilder._fmt_num(score, 3) if score is not None else "-",
                        "caption": f"「{name}」相对重要性",
                    }
                )
            if top:
                headline = (
                    f"机器学习里「{top.get('feature')}」相对最重要"
                    "（只解释这一次，不能外推）。"
                )
            return {
                "status": status,
                "headline": headline,
                "ranking": ranking,
                "next_steps": ["对照上面的多指标排序，看两边是否指向同一条件。"],
            }
        reason = str(block.get("reason") or xgb.get("reason") or "")
        if reason == "missing_dependency":
            headline = f"未安装 {xgb.get('dependency') or 'xgboost'}，跳过机器学习解释。"
        elif reason == "insufficient_samples":
            headline = (
                f"样本 {block.get('n')} 笔不足"
                f"（建议 ≥{block.get('required_samples', 500)}），暂不做机器学习解释。"
            )
        elif reason == "insufficient_varying_fields":
            headline = "变化条件不足 2 个，暂不做机器学习解释。"
        else:
            headline = "这次没做机器学习解释。"
        return {
            "status": "skipped",
            "headline": headline,
            "reason": reason,
            "ranking": [],
            "next_steps": [],
        }
    @staticmethod
    def _rank_multivariate_features(block: Dict[str, Any]) -> List[Dict[str, str]]:
        ols = block.get("ols_weighted_roi") if isinstance(block.get("ols_weighted_roi"), dict) else {}
        logistic = block.get("logistic_win") if isinstance(block.get("logistic_win"), dict) else {}
        coefs = []
        if ols.get("status") == "ok":
            coefs = list(ols.get("coefficients") or [])
            kind = "收益"
        elif logistic.get("status") == "ok":
            coefs = list(logistic.get("coefficients") or [])
            kind = "胜率"
        else:
            return []
        ranked: List[Tuple[float, Dict[str, Any]]] = []
        for item in coefs:
            if not isinstance(item, dict) or item.get("coef") is None:
                continue
            ranked.append((abs(float(item["coef"])), item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        out: List[Dict[str, str]] = []
        for _, item in ranked[:4]:
            coef = float(item["coef"])
            direction = "越高越有利" if coef > 0 else "越高越不利"
            out.append(
                {
                    "key": str(item.get("feature") or "?"),
                    "value": f"{coef:+.3f}",
                    "caption": f"对{kind}：{direction}",
                }
            )
        return out
    @staticmethod
    def _run_comparison_insights(classical: Dict[str, Any]) -> Dict[str, Any]:
        """Plain-language block for current vs baseline decision-space diff."""
        block = (
            classical.get("run_comparison")
            if isinstance(classical.get("run_comparison"), dict)
            else {}
        )
        status = str(block.get("status") or "not_requested")
        if status == "not_requested":
            return {
                "status": "not_requested",
                "headline": None,
                "changes": [],
                "explains": [],
                "does_not_explain": [],
                "next_steps": [
                    "想比较「改阈值前后差在哪」，请带上 --baseline-version 再跑归因。",
                ],
            }
        if status != "ok":
            return {
                "status": status,
                "headline": "对照版本暂不可用。",
                "changes": [],
                "explains": [],
                "does_not_explain": ["这次没能完成两次回测对照。"],
                "next_steps": ["确认对照版本号存在，并重新跑 sa。"],
                "reason": block.get("reason"),
            }
        comparison = block.get("comparison") if isinstance(block.get("comparison"), dict) else {}
        settings_diff = comparison.get("settings_diff") or []
        capture_diff = comparison.get("capture_diff") or []
        coverage_diff = comparison.get("coverage_diff") or []
        baseline_vid = (
            block.get("baseline_version_id")
            or comparison.get("baseline_version_id")
            or "-"
        )
        current_vid = comparison.get("current_version_id") or "-"
        changes: List[Dict[str, str]] = []
        for item in settings_diff:
            if not isinstance(item, dict):
                continue
            changes.append(
                {
                    "kind": "settings",
                    "label": str(item.get("key") or "?"),
                    "detail": (
                        f"参数从 {InsightBuilder._fmt_plain(item.get('baseline'))} "
                        f"改成 {InsightBuilder._fmt_plain(item.get('current'))}"
                    ),
                }
            )
        for item in capture_diff:
            if not isinstance(item, dict):
                continue
            changes.append(
                {
                    "kind": "capture",
                    "label": str(item.get("key") or "?"),
                    "detail": InsightBuilder._capture_diff_plain(item),
                }
            )
        for item in coverage_diff:
            if not isinstance(item, dict):
                continue
            changes.append(
                {
                    "kind": "coverage",
                    "label": str(item.get("key") or "?"),
                    "detail": (
                        f"样本量/覆盖从 {InsightBuilder._fmt_plain(item.get('baseline'))} "
                        f"变为 {InsightBuilder._fmt_plain(item.get('current'))}"
                    ),
                }
            )
        if changes:
            first = changes[0]
            headline = (
                f"相对对照版 v{baseline_vid}：主要改了「{first['label']}」"
                f"（{first['detail']}）"
            )
            if len(changes) > 1:
                headline += f"等 {len(changes)} 处差异"
        else:
            headline = f"相对对照版 v{baseline_vid}：参数和现场条件几乎没变"
        explains: List[str] = []
        does_not: List[str] = [
            "对照只说明「两次配置/分布差在哪」，不直接比较总胜率或总收益。",
            "也不能据此断定哪一版更好——要结合各自整体成绩单一起看。",
        ]
        if settings_diff:
            keys = "、".join(str(i.get("key")) for i in settings_diff[:3] if isinstance(i, dict))
            explains.append(f"两次回测的固定参数不同（{keys}）。")
            explains.append("单次分档只解释各自那一版内部；参数好不好要看两版整体结果差。")
        elif capture_diff:
            explains.append("两次回测的现场条件分布不同，变化可能来自行情或进场样本差异。")
        elif not comparison.get("has_meaningful_diff"):
            explains.append("对照后几乎看不出配置差异；若你预期不同，请核对版本号是否选对。")
            does_not.append("「几乎没变」不等于两版赚钱一样多。")
        next_steps: List[str] = []
        if settings_diff:
            next_steps.append("打开两版整体成绩单，对照总收益/胜率是否随参数变好。")
            next_steps.append("若对照版更好，把当前参数改回或再试中间值，重新回测。")
        elif comparison.get("has_meaningful_diff"):
            next_steps.append("先确认样本覆盖差异是否来自行情区间，再决定要不要改策略。")
        else:
            next_steps.append("确认 baseline 版本确实改过参数；必要时重新 simulate 再 sa。")
        return {
            "status": "ok",
            "headline": headline,
            "baseline_version_id": str(baseline_vid),
            "current_version_id": str(current_vid),
            "changes": changes,
            "explains": explains,
            "does_not_explain": does_not,
            "next_steps": next_steps[:3],
        }
    @staticmethod
    def _capture_diff_plain(item: Dict[str, Any]) -> str:
        kind = str(item.get("kind") or "")
        if kind == "constant_value_changed":
            return (
                f"固定值从 {InsightBuilder._fmt_plain(item.get('baseline'))} "
                f"变成 {InsightBuilder._fmt_plain(item.get('current'))}"
            )
        if kind == "role_changed":
            return (
                f"角色从 {item.get('baseline_role')} 变成 {item.get('current_role')}"
            )
        if kind == "varying_range_changed":
            current = item.get("current") if isinstance(item.get("current"), dict) else {}
            baseline = item.get("baseline") if isinstance(item.get("baseline"), dict) else {}
            return (
                f"分布区间 "
                f"[{InsightBuilder._fmt_num(baseline.get('min'))}~{InsightBuilder._fmt_num(baseline.get('max'))}] → "
                f"[{InsightBuilder._fmt_num(current.get('min'))}~{InsightBuilder._fmt_num(current.get('max'))}]"
            )
        if kind == "presence_changed":
            return "这一条件在某一版里缺失"
        return "现场条件分布有变化"
    @staticmethod
    def _merge_next_steps(primary: Sequence[str], extra: Sequence[Any]) -> List[str]:
        out: List[str] = []
        seen = set()
        for item in list(primary) + list(extra):
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)
            if len(out) >= 4:
                break
        return out
    @staticmethod
    def _fmt_plain(value: Any) -> str:
        if value is None:
            return "（空）"
        number = InsightBuilder._as_float(value)
        if number is not None and not isinstance(value, bool):
            return InsightBuilder._fmt_num(number)
        text = str(value).strip()
        return text or "（空）"
    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    @staticmethod
    def _fmt_num(value: Any, digits: int = 1) -> str:
        number = InsightBuilder._as_float(value)
        if number is None:
            return "-"
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        return f"{number:.{digits}f}"
    @staticmethod
    def _fmt_p(value: Any) -> str:
        number = InsightBuilder._as_float(value)
        if number is None:
            return "-"
        if number < 0.001:
            return "< 0.001"
        return f"{number:.3f}"
