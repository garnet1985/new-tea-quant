"""滚动对照报告：每个窗口相对主 version，不在窗口之间排名。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore

# layer, key, label, style, include_delta
# style: count | ratio | percent | number。percent 入库已是百分数，胜率不再乘 100。
_METRICS: Tuple[Tuple[str, str, str, str, bool], ...] = (
    ("enum", "total_opportunities", "机会数", "count", True),
    ("enum", "trigger_stocks", "触发股票数", "count", True),
    ("enum", "cv", "时间分散", "number", True),
    ("price", "win_rate", "胜率", "percent", True),
    ("price", "avg_roi", "平均收益率", "ratio", True),
    ("price", "top5_trade_profit_share", "前5笔利润占比", "ratio", True),
    ("portfolio", "max_drawdown", "最大回撤", "ratio", True),
    ("portfolio", "sharpe_ratio", "夏普", "number", True),
    ("portfolio", "sortino_ratio", "Sortino", "number", True),
    ("portfolio", "calmar_ratio", "Calmar", "number", True),
    ("portfolio", "total_return", "账户收益", "ratio", False),
)

_LAYER_KINDS = (
    (SimulateKind.ENUMERATE, "enum"),
    (SimulateKind.PRICE_FACTOR, "price"),
    (SimulateKind.PORTFOLIO, "portfolio"),
)


def metric_specs() -> Tuple[Tuple[str, str, str, str, bool], ...]:
    """返回对照列定义。"""
    return _METRICS


def window_span(
    start: str,
    end: str,
    baseline_start: str,
    baseline_end: str,
) -> Dict[str, Optional[int]]:
    """日历日长度，以及和基准区间重叠的天数；无法解析时对应字段为 None。"""
    current = _inclusive_days(start, end)
    base = _inclusive_days(baseline_start, baseline_end)
    overlap = _overlap_days(start, end, baseline_start, baseline_end)
    if current is None or base is None:
        overlap = None
    return {"length_days": current, "overlap_days": overlap}


def load_version_metrics(folder: Path, version_id: str) -> Dict[str, Any]:
    """读一版三层总体报告里的对照列，缺报告时该格为 None。"""
    vid = str(version_id or "").strip()
    summaries: Dict[str, Dict[str, Any]] = {}
    for kind, name in _LAYER_KINDS:
        summaries[name] = _summary(folder, vid, kind)
    # 顶层导入会绕回 Analyzer，再进本包。
    from core.modules.strategy.core.engines.analyzer.steps.campaign.gather.price_ledger import (
        ledger_metrics_for_version,
    )

    ledger = ledger_metrics_for_version(folder, vid)
    if isinstance(ledger, dict) and ledger.get("top5_trade_profit_share") is not None:
        summaries["price"]["top5_trade_profit_share"] = ledger.get("top5_trade_profit_share")
    layers: Dict[str, Dict[str, Optional[float]]] = {}
    for layer, key, _label, _style, _delta in _METRICS:
        block = layers.setdefault(layer, {})
        block[key] = _as_float((summaries.get(layer) or {}).get(key))
    conclusion = str((summaries.get("enum") or {}).get("dispersion_conclusion") or "").strip()
    return {"layers": layers, "dispersion_conclusion": conclusion}


def compare_window(
    baseline: Mapping[str, Any],
    window: Mapping[str, Any],
    *,
    version_id: str,
    start: str,
    end: str,
    baseline_start: str,
    baseline_end: str,
) -> Dict[str, Any]:
    """一个窗口相对基准的差值，账户总收益只留原文。"""
    span = window_span(start, end, baseline_start, baseline_end)
    layers: Dict[str, Dict[str, Any]] = {}
    for layer, key, label, style, include_delta in _METRICS:
        base_value = _layer_value(baseline, layer, key)
        value = _layer_value(window, layer, key)
        cell: Dict[str, Any] = {
            "label": label,
            "style": style,
            "baseline": base_value,
            "value": value,
        }
        if include_delta:
            cell["delta"] = _delta(value, base_value)
        layers.setdefault(layer, {})[key] = cell
    return {
        "version_id": version_id,
        "start": start,
        "end": end,
        "label": f"{start}-{end}",
        "length_days": span["length_days"],
        "overlap_days": span["overlap_days"],
        "dispersion_conclusion": _dispersion_conclusion(window),
        "baseline_dispersion_conclusion": _dispersion_conclusion(baseline),
        "layers": layers,
    }


def build_baseline_record(
    metrics: Mapping[str, Any],
    *,
    version_id: str,
    start: str,
    end: str,
) -> Dict[str, Any]:
    """基准行：这次回测自己的数，没有差值。"""
    layers: Dict[str, Dict[str, Any]] = {}
    for layer, key, label, style, _include_delta in _METRICS:
        layers.setdefault(layer, {})[key] = {
            "label": label,
            "style": style,
            "value": _layer_value(metrics, layer, key),
        }
    span = window_span(start, end, start, end)
    return {
        "version_id": version_id,
        "start": start,
        "end": end,
        "label": f"{start}-{end}" if start and end else version_id,
        "length_days": span["length_days"],
        "dispersion_conclusion": str(metrics.get("dispersion_conclusion") or "").strip(),
        "layers": layers,
    }


def assemble_report(
    *,
    parent_version_id: str,
    baseline_start: str,
    baseline_end: str,
    baseline_metrics: Mapping[str, Any],
    windows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """拼一份没有结论句的对照报告，第一行是基准回测。"""
    return {
        "mode": "rolling",
        "parent_version_id": parent_version_id,
        "baseline": build_baseline_record(
            baseline_metrics,
            version_id=parent_version_id,
            start=baseline_start,
            end=baseline_end,
        ),
        "window_count": len(windows),
        "windows": [dict(item) for item in windows],
        "generated_at": datetime.now().isoformat(),
    }


def _summary(folder: Path, version_id: str, kind: SimulateKind) -> Dict[str, Any]:
    if not version_id:
        return {}
    try:
        store = ArtifactStore.resolve(folder, kind=kind, version_id=version_id)
    except FileNotFoundError:
        return {}
    try:
        raw = ArtifactStore.read_json_at(store.output_dir, "overall_report")
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    summary = raw.get("summary") if isinstance(raw, dict) else None
    return dict(summary) if isinstance(summary, dict) else {}


def _layer_value(metrics: Mapping[str, Any], layer: str, key: str) -> Optional[float]:
    layers = metrics.get("layers")
    if not isinstance(layers, dict):
        return None
    block = layers.get(layer)
    if not isinstance(block, dict):
        return None
    return _as_float(block.get(key))


def _dispersion_conclusion(metrics: Mapping[str, Any]) -> str:
    return str(metrics.get("dispersion_conclusion") or "").strip()


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _delta(value: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if value is None or baseline is None:
        return None
    return float(value) - float(baseline)


def _inclusive_days(start: str, end: str) -> Optional[int]:
    left = _parse_day(start)
    right = _parse_day(end)
    if left is None or right is None or right < left:
        return None
    return (right - left).days + 1


def _overlap_days(start: str, end: str, baseline_start: str, baseline_end: str) -> Optional[int]:
    left = _parse_day(start)
    right = _parse_day(end)
    base_left = _parse_day(baseline_start)
    base_right = _parse_day(baseline_end)
    if None in (left, right, base_left, base_right):
        return None
    assert left is not None and right is not None
    assert base_left is not None and base_right is not None
    bound_left = max(left, base_left)
    bound_right = min(right, base_right)
    if bound_right < bound_left:
        return 0
    return (bound_right - bound_left).days + 1


def _parse_day(text: str) -> Optional[datetime]:
    raw = str(text or "").strip()
    if len(raw) != 8 or not raw.isdigit():
        return None
    try:
        return datetime.strptime(raw, "%Y%m%d")
    except ValueError:
        return None
