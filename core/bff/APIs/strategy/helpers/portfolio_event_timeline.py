"""Attach full equity/drawdown series + trade markers to portfolio capitalMetrics.

Build logic lives in the portfolio report_manager; this module merges into BFF slots.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Sequence

from core.bff.shared.client_log import log_degraded
from core.modules.strategy.core.engines.portfolio.report_manager.event_timeline import (
    build_portfolio_event_timeline,
)


def attach_portfolio_event_timeline(
    slot: Dict[str, Any],
    output_dirs: Sequence[Path],
) -> Dict[str, Any]:
    """Merge timeline into ``capitalMetrics`` from the first readable version dir."""
    if not isinstance(slot, dict) or not slot:
        return slot
    metrics = slot.get("capitalMetrics")
    if not isinstance(metrics, dict) or not metrics:
        return slot
    has_curve = (
        isinstance(metrics.get("eventCurveLabels"), list)
        and len(metrics.get("eventCurveLabels") or []) >= 2
    )
    has_trades = isinstance(metrics.get("tradeEvents"), list)
    # 曲线与逐笔都已在位则跳过（含 tradeEvents=[] 的空成交）。
    if has_curve and has_trades:
        return slot
    try:
        initial_capital = float(metrics.get("initialCapital") or 0.0)
    except (TypeError, ValueError):
        initial_capital = 0.0
    for output_dir in output_dirs:
        try:
            timeline = build_portfolio_event_timeline(
                Path(output_dir),
                initial_capital=initial_capital,
            )
        except Exception as exc:
            log_degraded("report.portfolio.eventTimeline.build", exc, str(output_dir))
            continue
        if not timeline:
            continue
        out = dict(slot)
        merged = dict(metrics)
        if not has_curve:
            merged["eventCurveLabels"] = timeline["eventCurveLabels"]
            merged["eventCurveValues"] = timeline["eventCurveValues"]
            merged["eventDrawdownValues"] = timeline["eventDrawdownValues"]
        if not has_trades:
            merged["tradeEvents"] = timeline["tradeEvents"]
        out["capitalMetrics"] = merged
        return out
    return slot


__all__ = [
    "attach_portfolio_event_timeline",
    "build_portfolio_event_timeline",
]
