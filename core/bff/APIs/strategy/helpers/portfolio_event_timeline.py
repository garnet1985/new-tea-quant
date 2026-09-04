"""Attach full equity/drawdown series + trade markers to portfolio capitalMetrics.

Downsampled ``equityCurveLabels`` (≤80) cannot host trade dates. This DTO reads
``equity_curve.json`` / ``trades.json`` from the version dir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.infra.utils import Utils
from core.modules.strategy.core.engines.portfolio.report_manager.capital_metrics import (
    EquityCurves,
)
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.bff.shared.client_log import log_degraded


def _norm_date(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        normalized = Utils.date.normalize_str(text)
    except Exception:
        normalized = None
    if normalized:
        return str(normalized).strip()
    return text[:16]


def _load_json_list(store: ArtifactStore, name: str) -> List[Any]:
    path = store.file(name)
    if not path.is_file():
        return []
    try:
        raw = store.read_json(name)
    except Exception as exc:
        log_degraded("report.portfolio.eventTimeline.read", exc, f"{name}:{store.output_dir}")
        return []
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, dict):
        inner = raw.get(name) or raw.get("items") or raw.get("trades")
        if isinstance(inner, list):
            return list(inner)
    return []


def _curve_arrays(
    points: Sequence[Dict[str, Any]],
    *,
    initial_capital: float,
) -> tuple[List[str], List[float], List[float]]:
    labels: List[str] = []
    values: List[float] = []
    peak = float(initial_capital or 0.0)
    drawdown: List[float] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        labels.append(_norm_date(point.get("date")) or str(point.get("date") or "")[:16])
        eq = EquityCurves.point_equity(point)
        values.append(eq)
        peak = max(peak, eq)
        dd_pct = ((peak - eq) / peak * 100.0) if peak > 1e-9 else 0.0
        drawdown.append(round(dd_pct, 4))
    return labels, values, drawdown


def _opt_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _buy_cost(row: Dict[str, Any], *, shares: int, price: float) -> Optional[float]:
    total_cost = _opt_float(row.get("total_cost"))
    if total_cost is not None:
        return total_cost
    amount = _opt_float(row.get("amount"))
    if amount is not None:
        fees = _opt_float(row.get("fees")) or 0.0
        return amount + fees
    if shares > 0 and price > 0:
        return float(shares) * price
    return None


def _trade_events(rows: Sequence[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    buy_price_by_lot: Dict[tuple, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        side = str(row.get("side") or "").strip().lower()
        if side not in {"buy", "sell"}:
            continue
        date = _norm_date(row.get("date"))
        entity_id = str(row.get("entity_id") or "").strip()
        if not date or not entity_id:
            continue
        inv_id = str(row.get("investment_id") or "").strip()
        try:
            shares = int(row.get("shares") or 0)
        except (TypeError, ValueError):
            shares = 0
        try:
            raw_price = float(row.get("price") or 0.0)
        except (TypeError, ValueError):
            raw_price = 0.0
        # Legacy trades.json may carry a negative sell from qfq-ROI reconstruction.
        # Display floor is 0 (long stock cannot pay to exit); engine now uses exit_price_raw.
        price = max(0.0, raw_price)
        event: Dict[str, Any] = {
            "date": date,
            "side": side,
            "entityId": entity_id,
            "stockName": entity_id,
            "shares": shares,
            "price": price,
        }
        if side == "buy":
            cost = _buy_cost(row, shares=shares, price=price)
            if cost is not None:
                event["cost"] = cost
            if inv_id and price > 0:
                buy_price_by_lot[(entity_id, inv_id)] = price
        else:
            profit = _opt_float(row.get("profit"))
            buy_px = buy_price_by_lot.get((entity_id, inv_id)) if inv_id else None
            if buy_px is None and profit is not None and shares > 0:
                inferred = raw_price - (profit / float(shares))
                if inferred > 0:
                    buy_px = inferred
            if buy_px is not None and buy_px > 0:
                event["buyPrice"] = buy_px
            if raw_price < 0 and buy_px and shares > 0:
                event["profit"] = float(shares) * (price - buy_px)
            elif profit is not None:
                event["profit"] = profit
        out.append(event)
    return out


def _enrich_stock_names(events: List[Dict[str, Any]]) -> None:
    codes = list(dict.fromkeys(str(e.get("entityId") or "") for e in events if e.get("entityId")))
    if not codes:
        return
    names: Dict[str, str] = {}
    try:
        from core.modules.data_manager import DataManager

        model = DataManager().get_table("sys_stock_list")
        if model is None:
            return
        chunk_size = 500
        for i in range(0, len(codes), chunk_size):
            chunk = codes[i : i + chunk_size]
            ph = ",".join(["%s"] * len(chunk))
            rows = model.load(f"id IN ({ph})", tuple(chunk))
            for rec in rows or []:
                row = dict(rec or {})
                sid = str(row.get("id") or "").strip()
                nm = str(row.get("name") or "").strip()
                if sid and nm:
                    names[sid] = nm
    except Exception as exc:
        log_degraded("report.portfolio.eventTimeline.stockNames", exc, f"n={len(codes)}")
        return
    if not names:
        return
    for event in events:
        sid = str(event.get("entityId") or "")
        nm = names.get(sid)
        if nm:
            event["stockName"] = nm


def build_portfolio_event_timeline(
    output_dir: Path,
    *,
    initial_capital: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """Return camelCase timeline fields, or ``None`` if the curve file is missing."""
    directory = Path(output_dir)
    if not directory.is_dir():
        return None
    store = ArtifactStore.at(directory, kind="portfolio")
    raw_curve = _load_json_list(store, "equity_curve")
    points = [p for p in raw_curve if isinstance(p, dict)]
    if len(points) < 2:
        return None
    labels, values, drawdown = _curve_arrays(points, initial_capital=initial_capital)
    if len(labels) < 2 or len(labels) != len(values):
        return None
    events = _trade_events(_load_json_list(store, "trades"))
    _enrich_stock_names(events)
    return {
        "eventCurveLabels": labels,
        "eventCurveValues": values,
        "eventDrawdownValues": drawdown,
        "tradeEvents": events,
    }


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
    if (
        isinstance(metrics.get("eventCurveLabels"), list)
        and len(metrics.get("eventCurveLabels") or []) >= 2
    ):
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
        merged.update(timeline)
        out["capitalMetrics"] = merged
        return out
    return slot


__all__ = [
    "attach_portfolio_event_timeline",
    "build_portfolio_event_timeline",
]
