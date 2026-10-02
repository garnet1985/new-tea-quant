"""从组合 overall_report + trades，对照价格账本收集买到 / 漏掉。"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.analyzer.steps.layer.consts import (
    EXIT_LABELS,
    PORTFOLIO_DISCLAIMER,
)
from core.modules.strategy.core.engines.analyzer.steps.layer.price_gather import (
    PriceGather,
    _is_book,
    _is_completed,
    _mean,
    _share,
)
from core.modules.strategy.core.engines.portfolio.data_class.trade import Trade
from core.modules.strategy.core.engines.portfolio.report_manager.capital_metrics import (
    EquityCurves,
)
from core.modules.strategy.core.engines.portfolio.report_manager.overall_report import (
    OverallReport as PortfolioOverallReport,
    OverallSummary as PortfolioOverallSummary,
)
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResultsManager,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    AllocationConfig,
    PortfolioSettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.io import ArtifactIO
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.artifacts.tables.price_investments import (
    PriceInvestmentRow,
)

Priced = Tuple[str, PriceInvestmentRow]


class PortfolioGather:
    """单 version 组合诊断；价格账本是全集。不做 SHAP。"""

    @classmethod
    def run(cls, store: ArtifactStore) -> Dict[str, Any]:
        summary = cls._load_summary(store)
        trades = cls._load_trades(store)
        alloc = cls._allocation(store)
        priced = cls._load_price_book(store)
        snapshots = cls._load_snapshots(store)
        book = [(eid, row) for eid, row in priced if _is_book(row) and _is_completed(row)]
        taken_keys = {
            (str(trade.entity_id), str(trade.investment_id))
            for trade in trades
            if trade.is_buy() and str(trade.entity_id) and str(trade.investment_id)
        }
        taken, leftover = _split_book(book, taken_keys)
        return {
            "disclaimer": PORTFOLIO_DISCLAIMER,
            "price_available": bool(priced),
            "allocation": {
                "mode": alloc.mode,
                "max_portfolio_size": int(alloc.max_portfolio_size or 0),
                "max_weight_per_stock": float(alloc.max_weight_per_stock or 0.0),
                "skip_trade_when_insufficient": bool(
                    alloc.skip_trade_when_insufficient
                ),
            },
            "fill": cls._fill(summary, alloc, book, taken, leftover),
            "taken_vs_leftover": cls._quality(taken, leftover),
            "groups": cls._groups(taken, leftover, snapshots),
            "drawdown": cls._drawdown(store, summary),
        }

    @staticmethod
    def _load_summary(store: ArtifactStore) -> PortfolioOverallSummary:
        path = store.file("overall_report")
        if not path.is_file():
            return PortfolioOverallSummary()
        return PortfolioOverallReport.load(store.output_dir).summary

    @staticmethod
    def _load_trades(store: ArtifactStore) -> List[Trade]:
        path = store.file("trades")
        if not path.is_file():
            return []
        raw = ArtifactIO.read_json(path)
        rows = raw if isinstance(raw, list) else []
        out: List[Trade] = []
        for item in rows:
            if isinstance(item, dict):
                out.append(Trade.from_dict(item))
        return out

    @staticmethod
    def _allocation(store: ArtifactStore) -> AllocationConfig:
        version_dir = store.output_dir.parent
        vid = str(store.version_id or version_dir.name or "").strip()
        if not vid:
            return AllocationConfig()
        payload = VersionMetaStore.read_effective_settings(version_dir.parent, vid) or {}
        return PortfolioSettings(dict(payload)).allocation

    @staticmethod
    def _load_price_book(store: ArtifactStore) -> List[Priced]:
        price_dir = store.output_dir.parent / ArtifactStore.step_dir_name(
            SimulateKind.PRICE_FACTOR
        )
        if not price_dir.is_dir():
            return []
        price_store = ArtifactStore.at(
            price_dir, kind=SimulateKind.PRICE_FACTOR, version_id=store.version_id
        )
        return PriceGather._load_priced(price_store)

    @staticmethod
    def _load_snapshots(store: ArtifactStore) -> Dict[Tuple[str, str], Dict[str, Any]]:
        enum_dir = store.output_dir.parent / ArtifactStore.step_dir_name(
            SimulateKind.ENUMERATE
        )
        if not enum_dir.is_dir():
            return {}
        manager = EnumResultsManager.at(enum_dir)
        out: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for row in manager.for_entities(manager.list_entities()):
            eid = str(row.entity_id or "").strip()
            iid = str(row.investment_id or "").strip()
            if eid and iid:
                out[(eid, iid)] = dict(row.signal_snapshot or {})
        return out

    @classmethod
    def _fill(
        cls,
        summary: PortfolioOverallSummary,
        alloc: AllocationConfig,
        book: Sequence[Priced],
        taken: Sequence[Priced],
        leftover: Sequence[Priced],
    ) -> Dict[str, Any]:
        curves = summary.curves
        peak = int(curves.peak_open_positions or 0)
        slots = int(alloc.max_portfolio_size or 0)
        return {
            "price_completed": len(book),
            "taken_count": len(taken),
            "leftover_count": len(leftover),
            "fill_ratio": _share(len(taken), len(book)),
            "buy_trades": int(summary.buy_trades or 0),
            "completed_investments": int(summary.completed_investments or 0),
            "total_return": float(summary.total_return or 0.0),
            "win_rate": float(summary.win_rate or 0.0),
            "avg_open_positions": float(curves.average_open_positions or 0.0),
            "peak_open_positions": peak,
            "max_portfolio_size": slots,
            "slots_at_cap": bool(slots > 0 and peak >= slots),
            "capital_utilization_ratio_pct": float(
                curves.capital_utilization_ratio_pct or 0.0
            ),
            "peak_capital_utilization_ratio_pct": float(
                curves.peak_capital_utilization_ratio_pct or 0.0
            ),
            "full_exposure_days_ratio_pct": float(
                curves.full_exposure_days_ratio_pct or 0.0
            ),
            "max_drawdown": float(curves.max_drawdown or 0.0),
            "top5_profit_concentration_pct": float(
                summary.quality.top5_profit_concentration_pct or 0.0
            ),
        }

    @classmethod
    def _quality(cls, taken: Sequence[Priced], leftover: Sequence[Priced]) -> Dict[str, Any]:
        taken_stats = _roi_stats(taken)
        leftover_stats = _roi_stats(leftover)
        taken_avg = taken_stats.get("avg_roi")
        leftover_avg = leftover_stats.get("avg_roi")
        gap = None
        if taken_avg is not None and leftover_avg is not None:
            gap = round(float(leftover_avg) - float(taken_avg), 4)
        return {
            "taken": taken_stats,
            "leftover": leftover_stats,
            "roi_gap": gap,
        }

    @classmethod
    def _groups(
        cls,
        taken: Sequence[Priced],
        leftover: Sequence[Priced],
        snapshots: Mapping[Tuple[str, str], Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        out.extend(_group_by("exit", taken, leftover, lambda item: _exit_label(item[1])))
        out.extend(_group_by("year", taken, leftover, lambda item: _year_key(item[1])))
        if snapshots:
            out.extend(
                _group_by(
                    "rsi",
                    taken,
                    leftover,
                    lambda item: _rsi_bin(_snapshot_of(item, snapshots)),
                )
            )
        return out

    @staticmethod
    def _drawdown(store: ArtifactStore, summary: PortfolioOverallSummary) -> Dict[str, Any]:
        path = store.file("equity_curve")
        peak_open = int(summary.curves.peak_open_positions or 0)
        if not path.is_file():
            return {"peak_open_in_drawdown": None, "peak_open_positions": peak_open}
        raw = ArtifactIO.read_json(path)
        points = raw if isinstance(raw, list) else []
        peak_eq = 0.0
        open_in_dd = 0
        for item in points:
            if not isinstance(item, dict):
                continue
            equity = EquityCurves.point_equity(item)
            peak_eq = max(peak_eq, equity)
            if peak_eq > 1e-9 and equity < peak_eq - 1e-9:
                open_in_dd = max(open_in_dd, int(item.get("open_positions") or 0))
        return {
            "peak_open_in_drawdown": open_in_dd,
            "peak_open_positions": peak_open,
        }


def _split_book(
    book: Sequence[Priced], taken_keys: set
) -> Tuple[List[Priced], List[Priced]]:
    taken: List[Priced] = []
    leftover: List[Priced] = []
    for eid, row in book:
        key = (eid, str(row.opportunity_id or "").strip())
        if key in taken_keys:
            taken.append((eid, row))
        else:
            leftover.append((eid, row))
    return taken, leftover


def _roi_stats(rows: Sequence[Priced]) -> Dict[str, Any]:
    rois = [float(row.roi or 0.0) for _, row in rows]
    wins = sum(1 for roi in rois if roi > 0)
    return {
        "count": len(rows),
        "avg_roi": _mean(rois),
        "win_rate": _share(wins, len(rows)),
    }


def _snapshot_of(
    item: Priced, snapshots: Mapping[Tuple[str, str], Dict[str, Any]]
) -> Optional[Mapping[str, Any]]:
    eid, row = item
    return snapshots.get((eid, str(row.opportunity_id or "").strip()))


def _group_by(
    kind: str,
    taken: Sequence[Priced],
    leftover: Sequence[Priced],
    key_fn: Callable[[Priced], str],
) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, List[Priced]]] = defaultdict(
        lambda: {"taken": [], "leftover": []}
    )
    for item in taken:
        buckets[str(key_fn(item) or "其他")]["taken"].append(item)
    for item in leftover:
        buckets[str(key_fn(item) or "其他")]["leftover"].append(item)
    out: List[Dict[str, Any]] = []
    for name in sorted(buckets):
        part = buckets[name]
        combined = part["taken"] + part["leftover"]
        stats = _roi_stats(combined)
        taken_stats = _roi_stats(part["taken"])
        out.append(
            {
                "kind": kind,
                "name": name,
                "price_count": stats["count"],
                "price_avg_roi": stats["avg_roi"],
                "taken_count": taken_stats["count"],
                "taken_avg_roi": taken_stats["avg_roi"],
                "leftover_count": _roi_stats(part["leftover"])["count"],
            }
        )
    return out


def _exit_label(row: PriceInvestmentRow) -> str:
    reason = str(row.exit_reason or "").strip() or "unknown"
    return EXIT_LABELS.get(reason, reason)


def _year_key(row: PriceInvestmentRow) -> str:
    text = str(row.enter_date or row.exit_date or "").strip()
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else "其他"


def _rsi_bin(snapshot: Optional[Mapping[str, Any]]) -> str:
    if not snapshot:
        return "无RSI"
    raw = snapshot.get("rsi")
    if raw is None:
        for key, value in snapshot.items():
            if str(key).lower().startswith("rsi") and value is not None:
                raw = value
                break
    try:
        rsi = float(raw)
    except (TypeError, ValueError):
        return "无RSI"
    if rsi < 15:
        return "RSI<15"
    if rsi < 20:
        return "RSI15-20"
    return "RSI≥20"
