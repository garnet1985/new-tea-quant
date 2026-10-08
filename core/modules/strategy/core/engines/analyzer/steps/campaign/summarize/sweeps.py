"""单因素参数扫描：每轴曲线 + 按主指标起伏的敏感度排名。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..contrasts import KnobContrasts
from ..labels import CampaignLabels
from . import value_ladders as ladders


def build_parameter_sweeps(
    gathered: Optional[Mapping[str, Any]],
    *,
    layer: str,
    primary_outcome: str,
    extra_outcomes: Sequence[str] = (),
    knob_prefixes: Sequence[str] = (),
) -> Dict[str, Any]:
    """从 gather 行构建 ``sweeps`` 与 ``sensitivity_rank``。"""
    rows = ladders.ready_rows(gathered, layer=layer)
    knobs = ladders.ladder_knobs(rows)
    if knob_prefixes:
        knobs = [
            path for path in knobs if ladders.knob_allowed(path, knob_prefixes)
        ]
    outcomes = list(
        dict.fromkeys([primary_outcome, *[str(item) for item in extra_outcomes]])
    )
    baseline = ladders.baseline_row(rows)
    sweeps: List[Dict[str, Any]] = []
    for knob in knobs:
        sweep = _one_sweep(
            rows,
            layer=layer,
            knob=knob,
            outcomes=outcomes,
            primary_outcome=primary_outcome,
            baseline=baseline,
        )
        if sweep is not None:
            sweeps.append(sweep)

    ranked = sorted(
        sweeps,
        key=lambda item: float(item.get("span") or 0.0),
        reverse=True,
    )
    sensitivity_rank = [
        {
            "rank": i + 1,
            "knob": item["knob"],
            "knob_label": item["knob_label"],
            "primary_outcome": primary_outcome,
            "span": item["span"],
            "span_label": item["span_label"],
            "best_value": (item.get("best") or {}).get("value"),
            "best_value_label": (item.get("best") or {}).get("value_label"),
            "best_metric": (item.get("best") or {}).get("metrics", {}).get(
                primary_outcome
            ),
            "impact": _impact_bucket(float(item.get("span") or 0.0), primary_outcome),
        }
        for i, item in enumerate(ranked)
    ]
    return {
        "primary_outcome": primary_outcome,
        "sweeps": sweeps,
        "sensitivity_rank": sensitivity_rank,
        "scope_note": (
            "单因素扫描：每次只改一个参数，其余保持当前配置。"
            "较优点为样本内结果，换窗口请用滚动验证。"
        ),
    }


def _one_sweep(
    rows: Sequence[Mapping[str, Any]],
    *,
    layer: str,
    knob: str,
    outcomes: Sequence[str],
    primary_outcome: str,
    baseline: Optional[Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    by_key: Dict[Any, Dict[str, Any]] = {}
    baseline_value = None
    if baseline is not None:
        knobs = baseline.get("knobs") if isinstance(baseline.get("knobs"), dict) else {}
        baseline_value = knobs.get(knob)

    for row in rows:
        if not ladders.row_is_ladder_point(row, knob):
            continue
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        raw_val = knobs.get(knob)
        key = ladders.value_key(raw_val)
        block = (row.get("layers") or {}).get(layer)
        if not isinstance(block, Mapping):
            continue
        metrics: Dict[str, float] = {}
        for outcome in outcomes:
            try:
                metrics[outcome] = float(block.get(outcome))
            except (TypeError, ValueError):
                continue
        if primary_outcome not in metrics:
            continue
        if key in by_key:
            continue
        by_key[key] = {
            "value": raw_val,
            "value_label": CampaignLabels.format_knob(knob, raw_val),
            "metrics": metrics,
            "version_id": row.get("version_id"),
            "is_baseline": ladders.value_key(raw_val) == ladders.value_key(baseline_value)
            and baseline is not None,
        }

    levels = list(by_key.values())
    if len(levels) < 2:
        return None

    display = ladders.sort_levels_display(
        [
            {
                "value": item["value"],
                "metric": item["metrics"][primary_outcome],
                "version_id": item.get("version_id"),
                "is_baseline": item.get("is_baseline"),
            }
            for item in levels
        ]
    )
    # 按展示顺序补回完整指标
    keyed = {ladders.value_key(item["value"]): item for item in levels}
    ordered: List[Dict[str, Any]] = []
    for item in display:
        full = keyed.get(ladders.value_key(item.get("value")))
        if full is None:
            continue
        ordered.append(full)

    primary_vals = [float(item["metrics"][primary_outcome]) for item in ordered]
    span = max(primary_vals) - min(primary_vals) if primary_vals else 0.0
    higher_better = CampaignLabels.higher_is_better(primary_outcome)
    reverse = True if higher_better is not False else False
    ranked = sorted(
        ordered,
        key=lambda item: float(item["metrics"][primary_outcome]),
        reverse=reverse,
    )
    best = ranked[0]
    worst = ranked[-1]
    return {
        "knob": knob,
        "knob_label": CampaignLabels.knob_label(knob),
        "primary_outcome": primary_outcome,
        "primary_outcome_label": CampaignLabels.outcome_label(primary_outcome),
        "higher_better": higher_better,
        "levels": ordered,
        "best": best,
        "worst": worst,
        "span": round(span, 6),
        "span_label": CampaignLabels.format_delta(primary_outcome, span)
        if span
        else CampaignLabels.format_number(primary_outcome, 0.0),
        "plateau": _plateau(
            ordered,
            primary_outcome=primary_outcome,
            best_metric=float(best["metrics"][primary_outcome]),
        ),
        "advice": _advice_line(
            knob=knob,
            primary_outcome=primary_outcome,
            best=best,
            span=span,
            ordered=ordered,
        ),
    }


def _plateau(
    ordered: Sequence[Mapping[str, Any]],
    *,
    primary_outcome: str,
    best_metric: float,
) -> Dict[str, Any]:
    """样本内接近最优的取值区间（按展示序）。"""
    eps = ladders.trend_eps(
        primary_outcome,
        [float(item["metrics"][primary_outcome]) for item in ordered],
    )
    tol = max(eps * 5, abs(best_metric) * 0.05, 1e-9)
    near = [
        item
        for item in ordered
        if abs(float(item["metrics"][primary_outcome]) - best_metric) <= tol
    ]
    if len(near) < 2:
        return {}
    return {
        "from_value": near[0].get("value"),
        "to_value": near[-1].get("value"),
        "from_label": near[0].get("value_label"),
        "to_label": near[-1].get("value_label"),
        "tolerance": round(tol, 6),
    }


def _advice_line(
    *,
    knob: str,
    primary_outcome: str,
    best: Mapping[str, Any],
    span: float,
    ordered: Sequence[Mapping[str, Any]],
) -> str:
    outcome_label = CampaignLabels.outcome_label(primary_outcome)
    best_val = CampaignLabels.format_knob(knob, best.get("value"))
    best_metric = (best.get("metrics") or {}).get(primary_outcome)
    metric_label = (
        CampaignLabels.format_number(primary_outcome, best_metric)
        if best_metric is not None
        else "—"
    )
    impact = _impact_bucket(span, primary_outcome)
    if impact == "小":
        return (
            f"在其余设置保持当前时，改 {CampaignLabels.knob_label(knob)} "
            f"对「{outcome_label}」影响小；不必优先纠结。"
            "（样本内；换窗口请用滚动验证。）"
        )
    plateau = _plateau(
        ordered,
        primary_outcome=primary_outcome,
        best_metric=float(best_metric) if best_metric is not None else 0.0,
    )
    plateau_bit = ""
    if plateau:
        plateau_bit = (
            f" {plateau.get('from_label')}～{plateau.get('to_label')} 较平（稳健区间）。"
        )
    return (
        f"在其余设置保持当前时，样本内「{outcome_label}」较好的取值约 "
        f"{best_val}（{metric_label}）。影响{impact}。{plateau_bit}"
        "换窗口请用滚动验证。"
    )


def _impact_bucket(span: float, outcome: str) -> str:
    eps = ladders.trend_eps(outcome, [0.0, abs(span) or 1.0])
    if abs(span) <= eps * 5:
        return "小"
    peak = abs(span)
    # 按这类指标的常见量级粗分
    last = str(outcome or "").split(".")[-1]
    if last in {"total_opportunities", "trigger_stocks", "total_completed_investments"}:
        if peak >= 500:
            return "大"
        if peak >= 100:
            return "中"
        return "小"
    if last in {"total_profit", "avg_profit_per_investment"}:
        if peak >= 50:
            return "大"
        if peak >= 10:
            return "中"
        return "小"
    # 比率和收益率
    if peak >= 0.08:
        return "大"
    if peak >= 0.02:
        return "中"
    return "小"


__all__ = ["build_parameter_sweeps"]
