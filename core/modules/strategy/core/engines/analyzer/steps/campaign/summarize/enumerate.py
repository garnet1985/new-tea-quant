"""枚举层战役总结（sea）：非交叉时按旋钮讲取值阶梯（最多/最少/趋势/对照表）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

from ..contrasts import KnobContrasts
from ..gather.enum_exits import after_take_profit_probe, baseline_exit_diagnosis
from ..labels import CampaignLabels
from ..metrics import READY
from .base import SummarizeBase

_SCOPE_NOTE_OAAT = "当前归因为单个参数对结果的归因"
_SCOPE_NOTE_CROSS = "当前归因为多个参数对结果的共同影响归因"

# 节 → 只采用这些路径前缀上的对照（避免 goal 进机会数叙事）
_SECTION_KNOB_PREFIXES = {
    "opportunity": ("core.", "data.", "sampling."),
    "stock_distribution": ("core.", "data.", "sampling."),
    "dispersion": ("core.", "data.", "sampling."),
    "exit_quality": ("goal.",),
}

_SECTION_META = (
    (
        "opportunity",
        "各个参数是如何影响回测找到的机会总数？",
        ("total_opportunities",),
    ),
    (
        "stock_distribution",
        "各个参数是如何影响机会的在股票间的分布？",
        ("trigger_ratio", "top_bucket_ratio"),
    ),
    (
        "dispersion",
        "各个参数是如何影响单只票的所有机会在回测区间的分散度？",
        ("cv",),
    ),
    (
        "exit_quality",
        "止损与止盈的不同取值是如何影响股票亏损与盈利的比例？",
        ("stop_loss_ratio", "take_profit_ratio"),
    ),
)

class EnumerateSummarize(SummarizeBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE

    @classmethod
    def run(
        cls,
        attributed: Mapping[str, Any],
        *,
        layer: str = "",
        folder: Any = None,
        gathered: Optional[Mapping[str, Any]] = None,
        executed: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        base = super().run(attributed, layer=layer or cls.LAYER)
        root = Path(folder) if folder is not None else None
        baseline_vid = _baseline_version_id(executed, gathered)
        cross = _is_cross(executed, gathered)
        sections = cls._build_sections(
            gathered=gathered,
            folder=root,
            baseline_vid=baseline_vid,
        )
        base["scope_note"] = _SCOPE_NOTE_CROSS if cross else _SCOPE_NOTE_OAAT
        base["analysis_mode"] = "cross" if cross else "oaat"
        base["sections"] = sections
        base["baseline_version_id"] = baseline_vid
        # 枚举报告按主题分节阅读，不再写顶栏孤立 headline。
        base["headline"] = ""
        return base

    @classmethod
    def _build_sections(
        cls,
        *,
        gathered: Optional[Mapping[str, Any]],
        folder: Optional[Path],
        baseline_vid: str,
    ) -> Dict[str, Any]:
        rows = _ready_rows(gathered)
        knobs = _ladder_knobs(rows)
        baseline_metrics = _baseline_metrics(rows)
        sections: Dict[str, Any] = {}
        for key, question, outcomes in _SECTION_META:
            prefixes = _SECTION_KNOB_PREFIXES.get(key) or ()
            section_knobs = [k for k in knobs if _knob_allowed(k, prefixes)]
            effects: List[Dict[str, Any]] = []
            for outcome in outcomes:
                for knob in section_knobs:
                    ladder = _value_ladder(rows, knob=knob, outcome=outcome)
                    if len(ladder.get("levels") or []) < 2:
                        continue
                    effect = _effect_block(
                        ladder,
                        baseline_metric=baseline_metrics.get(outcome),
                    )
                    if effect:
                        effects.append(effect)
            sections[key] = {
                "question": question,
                "outcomes": list(outcomes),
                "effects": effects,
                "facts": _facts_from_effects(effects),
                "conclusion": _conclusion_from_effects(effects),
                "suggestion": "",
            }

        exit_sec = sections["exit_quality"]
        if folder is not None and baseline_vid:
            diagnosis = baseline_exit_diagnosis(folder, baseline_vid)
            exit_sec["baseline"] = diagnosis
            extra = _exit_fact_lines(diagnosis)
            if extra:
                exit_sec["facts"] = list(exit_sec.get("facts") or []) + extra
            if diagnosis.get("high_stop_loss_stocks"):
                base_c = str(exit_sec.get("conclusion") or "").rstrip("。")
                note = "止损在当前策略配置下集中在少数票或少数月份"
                if note not in base_c:
                    exit_sec["conclusion"] = (
                        f"{base_c}；{note}。" if base_c else f"{note}。"
                    )

        settings = _effective_settings(folder, baseline_vid) if folder else None
        if folder is not None and baseline_vid:
            after = after_take_profit_probe(folder, baseline_vid, settings)
            # 得不到结论时不写这一节，避免空话占版面。
            if after.get("available"):
                sections["after_take_profit"] = {
                    "question": "止盈后面还有没有涨（仅当分档或动态止盈真跑过）",
                    "effects": [],
                    "facts": list(after.get("facts") or []),
                    "conclusion": str(
                        after.get("conclusion") or after.get("reason") or ""
                    ),
                    "suggestion": "",
                    "available": True,
                    "detail": after,
                }

        for key, section in sections.items():
            if key == "after_take_profit":
                continue
            if not (section.get("effects") or []):
                section["facts"] = ["本格没有可用的参数取值对照（或指标未变化）。"]
                section["conclusion"] = "只有基准格时，不能比较取值好坏。"
                section["suggestion"] = ""
        return sections


def _ready_rows(gathered: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(gathered, Mapping):
        return []
    out: List[Dict[str, Any]] = []
    for row in gathered.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "") not in READY:
            continue
        enum = (row.get("layers") or {}).get("enumerate")
        if not isinstance(enum, dict):
            continue
        out.append(row)
    return out


def _baseline_row(rows: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    for row in rows:
        overlay = row.get("overlay")
        if isinstance(overlay, dict) and not overlay:
            return row
    return None


def _baseline_metrics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    row = _baseline_row(rows)
    if row is None:
        return {}
    enum = (row.get("layers") or {}).get("enumerate")
    if not isinstance(enum, Mapping):
        return {}
    out: Dict[str, float] = {}
    for key, value in enum.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _ladder_knobs(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    """有 ≥2 个不同取值的旋钮路径（基准 + oaat 变体）。"""
    order: List[str] = []
    seen: set = set()
    for row in rows:
        knobs = row.get("knobs")
        if not isinstance(knobs, Mapping):
            continue
        for path in knobs:
            text = str(path)
            if text in seen:
                continue
            seen.add(text)
            order.append(text)
    usable: List[str] = []
    for path in order:
        values = {
            _value_key((row.get("knobs") or {}).get(path))
            for row in rows
            if _row_is_ladder_point(row, path)
        }
        if len(values) >= 2:
            usable.append(path)
    return usable


def _row_is_ladder_point(row: Mapping[str, Any], knob: str) -> bool:
    """基准格（无 overlay），或 overlay 只动这一条路径。"""
    overlay = row.get("overlay")
    if not isinstance(overlay, dict) or not overlay:
        return True
    return KnobContrasts.union_paths([overlay]) == [knob]


def _value_ladder(
    rows: Sequence[Mapping[str, Any]],
    *,
    knob: str,
    outcome: str,
) -> Dict[str, Any]:
    by_key: Dict[Any, Dict[str, Any]] = {}
    baseline = _baseline_row(rows)
    baseline_value = None
    if baseline is not None:
        knobs = baseline.get("knobs") if isinstance(baseline.get("knobs"), dict) else {}
        baseline_value = knobs.get(knob)

    for row in rows:
        if not _row_is_ladder_point(row, knob):
            continue
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        raw_val = knobs.get(knob)
        key = _value_key(raw_val)
        enum = (row.get("layers") or {}).get("enumerate")
        if not isinstance(enum, Mapping):
            continue
        try:
            number = float(enum.get(outcome))
        except (TypeError, ValueError):
            continue
        if key in by_key:
            continue
        by_key[key] = {
            "value": raw_val,
            "metric": number,
            "version_id": row.get("version_id"),
            "is_baseline": _value_key(raw_val) == _value_key(baseline_value)
            and baseline is not None,
        }
    levels = list(by_key.values())
    if len(levels) < 2:
        return {"knob": knob, "outcome": outcome, "levels": levels}
    higher_better = CampaignLabels.higher_is_better(outcome)
    reverse = True if higher_better is not False else False
    ranked = sorted(
        levels,
        key=lambda item: float(item["metric"]),
        reverse=reverse,
    )
    return {
        "knob": knob,
        "outcome": outcome,
        "higher_better": higher_better,
        "levels": _sort_levels_display(levels),
        "best": ranked[0],
        "worst": ranked[-1],
    }


def _sort_levels_display(levels: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """展示顺序：未使用优先，其余按数值/字符串。"""

    def sort_key(item: Mapping[str, Any]) -> Tuple[int, Any]:
        value = item.get("value")
        if value is None:
            return (0, "")
        scalar = KnobContrasts.scalar(value)
        if scalar is not None:
            return (1, float(scalar))
        return (2, str(value))

    return [dict(item) for item in sorted(levels, key=sort_key)]


def _effect_block(
    ladder: Mapping[str, Any],
    *,
    baseline_metric: Optional[float],
) -> Optional[Dict[str, Any]]:
    levels = [dict(item) for item in (ladder.get("levels") or []) if isinstance(item, dict)]
    if len(levels) < 2:
        return None
    knob = str(ladder.get("knob") or "")
    outcome = str(ladder.get("outcome") or "")
    label = CampaignLabels.knob_label(knob)
    outcome_label = CampaignLabels.outcome_label(outcome)
    best = ladder.get("best") if isinstance(ladder.get("best"), dict) else levels[0]
    worst = ladder.get("worst") if isinstance(ladder.get("worst"), dict) else levels[-1]

    table: List[Dict[str, Any]] = []
    for level in levels:
        metric = float(level["metric"])
        delta = None if baseline_metric is None else metric - float(baseline_metric)
        table.append(
            {
                "value": level.get("value"),
                "value_label": CampaignLabels.format_knob(knob, level.get("value")),
                "metric": metric,
                "metric_label": CampaignLabels.format_number(outcome, metric),
                "delta": delta,
                "delta_label": (
                    "当前配置"
                    if level.get("is_baseline")
                    else (
                        CampaignLabels.format_delta(outcome, delta)
                        if delta is not None
                        else "—"
                    )
                ),
                "is_baseline": bool(level.get("is_baseline")),
                "version_id": level.get("version_id"),
            }
        )

    title = f"{label} 对「{outcome_label}」的影响"
    best_v = CampaignLabels.format_knob(knob, best.get("value"))
    worst_v = CampaignLabels.format_knob(knob, worst.get("value"))
    # 结论只保留最好 / 最差 / 趋势，数值细节留给表格。
    max_line = f"最好情况：{best_v}"
    min_line = f"最差情况：{worst_v}"
    trend_line = _trend_line(knob=knob, outcome=outcome, levels=levels)
    return {
        "knob": knob,
        "knob_label": label,
        "outcome": outcome,
        "outcome_label": outcome_label,
        "title": title,
        "max_line": max_line,
        "min_line": min_line,
        "trend_line": trend_line,
        "table": table,
        "best": best,
        "worst": worst,
        "levels": levels,
        "higher_better": ladder.get("higher_better"),
    }


def _trend_line(
    *,
    knob: str,
    outcome: str,
    levels: Sequence[Mapping[str, Any]],
) -> str:
    outcome_label = CampaignLabels.outcome_label(outcome)
    numeric: List[Tuple[float, float]] = []
    for level in levels:
        scalar = KnobContrasts.scalar(level.get("value"))
        if scalar is None:
            continue
        try:
            numeric.append((float(scalar), float(level["metric"])))
        except (TypeError, ValueError, KeyError):
            continue
    numeric.sort(key=lambda item: item[0])

    if len(numeric) < 2:
        # 常见：None vs 一个阈值
        off = next((item for item in levels if item.get("value") is None), None)
        ons = [item for item in levels if item.get("value") is not None]
        if off is not None and len(ons) == 1:
            on = ons[0]
            try:
                delta = float(on["metric"]) - float(off["metric"])
            except (TypeError, ValueError, KeyError):
                return "趋势：只有「未使用」与单一取值，谈不上升降关系。"
            if abs(delta) <= _trend_eps(outcome, [float(off["metric"]), float(on["metric"])]):
                return f"趋势：启用后，「{outcome_label}」几乎不变。"
            direction = "升高" if delta > 0 else "降低"
            return f"趋势：相对未使用，启用后「{outcome_label}」{direction}。"
        return "趋势：可比较数值档不足，看不出与参数的关系。"

    metrics = [item[1] for item in numeric]
    eps = _trend_eps(outcome, metrics)
    non_decreasing = all(
        metrics[i] <= metrics[i + 1] + eps for i in range(len(metrics) - 1)
    )
    non_increasing = all(
        metrics[i] + eps >= metrics[i + 1] for i in range(len(metrics) - 1)
    )
    span = abs(metrics[-1] - metrics[0])
    if span <= eps:
        return f"趋势：参数越大，「{outcome_label}」几乎不变。"
    if non_decreasing and not non_increasing:
        return f"趋势：参数越大，「{outcome_label}」大致越高。"
    if non_increasing and not non_decreasing:
        return f"趋势：参数越大，「{outcome_label}」大致越低。"
    return f"趋势：「{outcome_label}」与参数取值没有明显的单调关系。"


def _trend_eps(outcome: str, metrics: Sequence[float]) -> float:
    if not metrics:
        return 1e-9
    peak = max(abs(float(item)) for item in metrics) or 1.0
    # 比例类约 0.5 个百分点；计数类至少 0.5
    last = str(outcome or "").split(".")[-1]
    if last.endswith("ratio") or last in {"win_rate", "avg_roi", "total_return", "cv"}:
        return max(0.005, peak * 1e-6)
    return max(0.5, peak * 1e-6)


def _facts_from_effects(effects: Sequence[Mapping[str, Any]]) -> List[str]:
    facts: List[str] = []
    for effect in effects:
        label = str(effect.get("knob_label") or effect.get("knob") or "").strip()
        bits = [
            str(effect.get(key) or "").strip()
            for key in ("max_line", "min_line", "trend_line")
            if str(effect.get(key) or "").strip()
        ]
        if label and bits:
            facts.append(f"{label} — {'；'.join(bits)}")
        elif bits:
            facts.extend(bits)
    return facts


def _conclusion_from_effects(effects: Sequence[Mapping[str, Any]]) -> str:
    facts = _facts_from_effects(effects)
    return " ".join(facts)


def _is_cross(
    executed: Optional[Mapping[str, Any]],
    gathered: Optional[Mapping[str, Any]],
) -> bool:
    if isinstance(executed, Mapping):
        for key in ("family", "mode", "parameter_mode"):
            if str(executed.get(key) or "").strip() == "cross":
                return True
    for row in _ready_rows(gathered):
        overlay = row.get("overlay")
        if not isinstance(overlay, dict) or not overlay:
            continue
        if len(KnobContrasts.union_paths([overlay])) > 1:
            return True
    return False


def _knob_allowed(knob: Any, prefixes: Optional[Sequence[str]]) -> bool:
    if not prefixes:
        return True
    text = str(knob or "").strip()
    return any(text.startswith(prefix) for prefix in prefixes)


def _value_key(value: Any) -> Any:
    if value is None:
        return ("off",)
    scalar = KnobContrasts.scalar(value)
    if scalar is not None:
        return ("num", round(float(scalar), 8))
    if isinstance(value, Mapping):
        return ("map", repr(sorted(value.items(), key=lambda item: str(item[0]))))
    return ("raw", repr(value))


def _baseline_version_id(
    executed: Optional[Mapping[str, Any]],
    gathered: Optional[Mapping[str, Any]],
) -> str:
    if isinstance(executed, Mapping):
        parent = str(executed.get("parent_version_id") or "").strip()
        if parent:
            return parent
    rows = _ready_rows(gathered)
    for row in rows:
        overlay = row.get("overlay")
        if isinstance(overlay, dict) and not overlay:
            vid = str(row.get("version_id") or "").strip()
            if vid:
                return vid
    for row in rows:
        vid = str(row.get("version_id") or "").strip()
        if vid and "-" not in vid:
            return vid
    return ""


def _effective_settings(
    folder: Optional[Path], version_id: str
) -> Optional[Dict[str, Any]]:
    if folder is None or not version_id:
        return None
    try:
        disk = VersionMetaStore.read_effective_settings(
            ArtifactStore.simulations_root(folder), version_id
        )
    except Exception:
        return None
    return disk if isinstance(disk, dict) else None


def _exit_fact_lines(diagnosis: Mapping[str, Any]) -> List[str]:
    lines: List[str] = []
    stocks = diagnosis.get("high_stop_loss_stocks") or []
    if isinstance(stocks, list) and stocks:
        bits = []
        for item in stocks[:3]:
            if not isinstance(item, dict):
                continue
            name = item.get("stock_name") or item.get("entity_id")
            ratio = item.get("stop_loss_ratio")
            bits.append(
                f"{name} 止损"
                f"{CampaignLabels.format_number('stop_loss_ratio', ratio)}"
                f"（{item.get('stop_loss')}/{item.get('n')}）"
            )
        if bits:
            lines.append("止损偏高的票：" + "；".join(bits) + "。")
    months = diagnosis.get("stop_loss_by_month") or []
    if isinstance(months, list) and months:
        bits = []
        for item in months[:3]:
            if not isinstance(item, dict):
                continue
            bits.append(
                f"{item.get('month')} "
                f"{CampaignLabels.format_number('stop_loss_ratio', item.get('stop_loss_ratio'))}"
            )
        if bits:
            lines.append("止损偏高的月份：" + "；".join(bits) + "。")
    return lines


__all__ = ["EnumerateSummarize"]
