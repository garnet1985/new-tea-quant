"""价格代表样本账本：从 price entities CSV 算集中度与出场利润贡献。"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.engines.price_factor.report_manager.report_scan import (
    PriceCsvScan,
)

_TOP_N = 5


def ledger_metrics_for_version(folder: Path, version_id: str) -> Dict[str, Any]:
    """读一版价格回测成交，产出归因用扁平指标。"""
    vid = str(version_id or "").strip()
    if not vid:
        return {}
    try:
        store = ArtifactStore.resolve(
            folder, kind=SimulateKind.PRICE_FACTOR, version_id=vid
        )
    except FileNotFoundError:
        return {}
    output_dir = Path(getattr(store, "output_dir", "") or "")
    if not output_dir.is_dir():
        return {}
    try:
        scan = PriceCsvScan.collect(output_dir, version_id=vid)
    except Exception:
        return {}
    return metrics_from_scan(scan)


def metrics_from_scan(scan: PriceCsvScan) -> Dict[str, Any]:
    """占比分母 = 各笔盈亏绝对值之和，避免净利润对冲后出现 >100%。"""
    trades: List[Tuple[float, float, str, str]] = []
    # (profit, roi, entity_id, exit_key)
    for entity_id, rows in (scan.investments_by_entity or {}).items():
        eid = str(entity_id or "").strip()
        for row in rows or []:
            if str(getattr(row, "skip_reason", "") or "").strip():
                continue
            if not str(getattr(row, "exit_date", "") or "").strip():
                continue
            roi = float(getattr(row, "roi", 0.0) or 0.0)
            enter = float(
                getattr(row, "enter_price_hfq", 0.0)
                or getattr(row, "enter_price", 0.0)
                or 0.0
            )
            profit = roi * enter if enter else roi
            reason = _normalize_exit(str(getattr(row, "exit_reason", "") or ""))
            trades.append((profit, roi, eid, reason))

    empty = {
        "n_completed": 0,
        "payoff_ratio": None,
        "top5_trade_profit_share": None,
        "top5_stock_profit_share": None,
        "avg_roi_without_top5": None,
        "take_profit_profit_share": None,
        "stop_loss_profit_share": None,
        "expire_profit_share": None,
    }
    if not trades:
        return empty

    rois = [item[1] for item in trades]
    wins = [r for r in rois if r > 0]
    losses = [r for r in rois if r < 0]
    payoff = None
    if wins and losses:
        mean_win = sum(wins) / len(wins)
        mean_loss = abs(sum(losses) / len(losses))
        if mean_loss > 1e-12:
            payoff = round(mean_win / mean_loss, 4)

    profits = [item[0] for item in trades]
    abs_mass = sum(abs(p) for p in profits)
    denom = abs_mass if abs_mass > 1e-12 else None

    ranked = sorted(trades, key=lambda item: item[0], reverse=True)
    top_trades = ranked[: min(_TOP_N, len(ranked))]
    top5_trade_share = (
        round(sum(item[0] for item in top_trades) / denom, 4) if denom else None
    )

    by_stock: Dict[str, float] = defaultdict(float)
    for profit, _roi, eid, _reason in trades:
        by_stock[eid or "?"] += profit
    stock_ranked = sorted(by_stock.values(), reverse=True)
    top5_stock_share = (
        round(sum(stock_ranked[: min(_TOP_N, len(stock_ranked))]) / denom, 4)
        if denom
        else None
    )

    keep_rois = [item[1] for item in ranked[min(_TOP_N, len(ranked)) :]]
    avg_without = (
        round(sum(keep_rois) / len(keep_rois), 4) if keep_rois else None
    )

    exit_profit: Dict[str, float] = defaultdict(float)
    for profit, _roi, _eid, reason in trades:
        exit_profit[reason] += profit

    def share(key: str) -> Optional[float]:
        if denom is None:
            return None
        return round(float(exit_profit.get(key, 0.0)) / denom, 4)

    return {
        "n_completed": len(trades),
        "payoff_ratio": payoff,
        "top5_trade_profit_share": top5_trade_share,
        "top5_stock_profit_share": top5_stock_share,
        "avg_roi_without_top5": avg_without,
        "take_profit_profit_share": share("take_profit"),
        "stop_loss_profit_share": share("stop_loss"),
        "expire_profit_share": share("expire"),
    }


def attach_price_ledger(
    folder: Path,
    version_id: str,
    layer_block: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not isinstance(layer_block, dict):
        return layer_block
    metrics = ledger_metrics_for_version(folder, version_id)
    if not metrics:
        return layer_block
    merged = dict(layer_block)
    for key, value in metrics.items():
        if key == "n_completed":
            continue
        merged[key] = value
    return merged


def _normalize_exit(reason: str) -> str:
    text = reason.strip().lower()
    if "take_profit" in text or text in {"tp", "win"}:
        return "take_profit"
    if "stop_loss" in text or text in {"sl", "loss"}:
        return "stop_loss"
    if "expir" in text or text in {"simulate_end", "end"}:
        return "expire"
    return text or "other"


__all__ = [
    "attach_price_ledger",
    "ledger_metrics_for_version",
    "metrics_from_scan",
]
