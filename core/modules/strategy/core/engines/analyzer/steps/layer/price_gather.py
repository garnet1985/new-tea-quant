"""从价格 overall_report + investments CSV 收集去噪账事实。"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.analyzer.steps.layer.consts import (
    EXIT_LABELS,
    PRICE_BOOK_DISCLAIMER,
    TOP_N,
)
from core.modules.strategy.core.engines.price_factor.report_manager.overall_report import (
    OverallReport as PriceOverallReport,
    OverallSummary as PriceOverallSummary,
)
from core.modules.strategy.core.engines.price_factor.report_manager.price_metrics import (
    SkipCounters,
)
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    PriceFactorStore,
    PriceInvestmentRow,
)

Priced = Tuple[str, PriceInvestmentRow]
EnumRow = Tuple[str, EnumResult]


class PriceGather:
    """单 version 价格账；对照枚举看合并 / 涨跌停偏，不做 SHAP。"""

    @classmethod
    def run(cls, store: ArtifactStore) -> Dict[str, Any]:
        priced = cls._load_priced(store)
        book = [(eid, row) for eid, row in priced if _is_book(row)]
        skipped = [
            (eid, row) for eid, row in priced if str(row.skip_reason or "").strip()
        ]
        summary = cls._load_summary(store)
        enum_rows = cls._load_enum(store)
        return {
            "disclaimer": PRICE_BOOK_DISCLAIMER,
            "book": cls._book(summary, book),
            "concentration": cls._concentration(book),
            "exits": cls._exits(book),
            "yearly": cls._yearly(book),
            "denoising": cls._denoising(priced, book, skipped, enum_rows, summary),
        }

    @staticmethod
    def _load_priced(store: ArtifactStore) -> List[Priced]:
        price = (
            store
            if isinstance(store, PriceFactorStore)
            else PriceFactorStore.at(store.output_dir, version_id=store.version_id)
        )
        ids = list(price.entity_ids or []) or price.list_investment_entities()
        out: List[Priced] = []
        for eid, rows in price.load_all_investments(ids).items():
            for row in rows:
                out.append((str(eid), row))
        return out

    @staticmethod
    def _load_summary(store: ArtifactStore) -> PriceOverallSummary:
        path = store.file("overall_report")
        if not path.is_file():
            return PriceOverallSummary()
        return PriceOverallReport.load(store.output_dir).summary

    @staticmethod
    def _load_enum(store: ArtifactStore) -> List[EnumRow]:
        enum_dir = store.output_dir.parent / ArtifactStore.step_dir_name(
            SimulateKind.ENUMERATE
        )
        if not enum_dir.is_dir():
            return []
        manager = EnumResultsManager.at(enum_dir)
        ids = manager.list_entities()
        return [
            (str(row.entity_id), row)
            for row in manager.for_entities(ids)
            if str(row.entity_id or "").strip()
        ]

    @classmethod
    def _book(
        cls,
        summary: PriceOverallSummary,
        book: Sequence[Priced],
    ) -> Dict[str, Any]:
        completed = [row for _, row in book if _is_completed(row)]
        rois = [float(row.roi or 0.0) for row in completed]
        wins = [roi for roi in rois if roi > 0]
        losses = [roi for roi in rois if roi < 0]
        avg_roi = _mean(rois)
        win_rate = _share(len(wins), len(completed))
        if not completed and summary.total_completed_investments:
            win_rate = _win_rate_from_summary(summary)
            avg_roi = float(summary.avg_roi or 0.0)
        return {
            "completed_count": len(completed)
            or int(summary.total_completed_investments or 0),
            "total_investments": len(book) or int(summary.total_investments or 0),
            "win_count": len(wins) or int(summary.total_win_investments or 0),
            "loss_count": len(losses) or int(summary.total_loss_investments or 0),
            "win_rate": win_rate,
            "avg_roi": avg_roi if avg_roi is not None else float(summary.avg_roi or 0.0),
            "profit_factor": _profit_factor(wins, losses),
            "total_profit": round(sum(_profit(row) for row in completed), 4),
            "roi_p50": float(summary.roi.roi_p50 or 0.0),
            "roi_iqr": float(summary.roi.roi_iqr or 0.0),
            "roi_conclusion": str(summary.roi.roi_conclusion or ""),
        }

    @classmethod
    def _concentration(cls, book: Sequence[Priced]) -> Dict[str, Any]:
        completed = [(eid, row) for eid, row in book if _is_completed(row)]
        ranked = sorted(
            completed, key=lambda item: float(item[1].roi or 0.0), reverse=True
        )
        gross = sum(max(float(row.roi or 0.0), 0.0) for _, row in completed)
        top_trades = ranked[:TOP_N]
        rest_trades = ranked[TOP_N:]
        without_trades = _mean([float(row.roi or 0.0) for _, row in rest_trades])
        stock_sums: Dict[str, float] = defaultdict(float)
        for eid, row in completed:
            stock_sums[eid] += float(row.roi or 0.0)
        top_stock_ids = {
            eid
            for eid, _ in sorted(
                stock_sums.items(), key=lambda item: item[1], reverse=True
            )[:TOP_N]
        }
        rest_stock_rois = [
            float(row.roi or 0.0)
            for eid, row in completed
            if eid not in top_stock_ids
        ]
        without_stocks = _mean(rest_stock_rois)
        top_stock_gross = sum(
            max(value, 0.0)
            for eid, value in stock_sums.items()
            if eid in top_stock_ids
        )
        top_trade_gross = sum(
            max(float(row.roi or 0.0), 0.0) for _, row in top_trades
        )
        return {
            "top5_trades_profit_share": _share_float(top_trade_gross, gross),
            "top5_stocks_profit_share": _share_float(top_stock_gross, gross),
            "avg_roi_without_top5_trades": without_trades,
            "avg_roi_without_top5_stocks": without_stocks,
            "still_positive_without_top5_trades": bool(
                without_trades is not None and without_trades > 0
            ),
            "still_positive_without_top5_stocks": bool(
                without_stocks is not None and without_stocks > 0
            ),
            "sample_count": len(completed),
        }

    @classmethod
    def _exits(cls, book: Sequence[Priced]) -> Dict[str, Any]:
        completed = [row for _, row in book if _is_completed(row)]
        groups: Dict[str, List[PriceInvestmentRow]] = defaultdict(list)
        for row in completed:
            reason = str(row.exit_reason or "").strip() or "unknown"
            groups[reason].append(row)
        total = len(completed)
        net = sum(_profit(row) for row in completed)
        mix = [
            cls._exit_row(reason, group, total, net)
            for reason, group in sorted(
                groups.items(), key=lambda item: (-len(item[1]), item[0])
            )
        ]
        return {"completed_count": total, "by_reason": mix}

    @staticmethod
    def _exit_row(
        reason: str,
        group: Sequence[PriceInvestmentRow],
        total: int,
        net: float,
    ) -> Dict[str, Any]:
        profit_sum = sum(_profit(row) for row in group)
        rois = [float(row.roi or 0.0) for row in group]
        return {
            "reason": reason,
            "label": EXIT_LABELS.get(reason, reason),
            "count": len(group),
            "share": _share(len(group), total),
            "mean_roi": _mean(rois),
            "profit_sum": round(profit_sum, 4),
            "profit_share": _share_float(profit_sum, net) if net else 0.0,
        }

    @classmethod
    def _yearly(cls, book: Sequence[Priced]) -> List[Dict[str, Any]]:
        groups: Dict[str, List[PriceInvestmentRow]] = defaultdict(list)
        for _, row in book:
            if not _is_completed(row):
                continue
            year = _year_key(row.enter_date or row.exit_date)
            if year:
                groups[year].append(row)
        out: List[Dict[str, Any]] = []
        for year in sorted(groups):
            rows = groups[year]
            rois = [float(row.roi or 0.0) for row in rows]
            wins = sum(1 for roi in rois if roi > 0)
            out.append(
                {
                    "year": year,
                    "count": len(rows),
                    "win_rate": _share(wins, len(rows)),
                    "avg_roi": _mean(rois),
                }
            )
        return out

    @classmethod
    def _denoising(
        cls,
        priced: Sequence[Priced],
        book: Sequence[Priced],
        skipped: Sequence[Priced],
        enum_rows: Sequence[EnumRow],
        summary: PriceOverallSummary,
    ) -> Dict[str, Any]:
        del summary
        skips = SkipCounters.compute([row for _, row in priced])
        price_keys = {
            (eid, str(row.opportunity_id or "").strip())
            for eid, row in priced
            if str(row.opportunity_id or "").strip()
        }
        enum_map = {
            (eid, str(row.investment_id or "").strip()): row
            for eid, row in enum_rows
            if str(row.investment_id or "").strip()
        }
        merged_rows = [row for key, row in enum_map.items() if key not in price_keys]
        skipped_enum = [
            enum_map[key]
            for key in (
                (eid, str(row.opportunity_id or "").strip()) for eid, row in skipped
            )
            if key in enum_map
        ]
        book_rois = [float(row.roi or 0.0) for _, row in book if _is_completed(row)]
        merged_rois = [float(row.weighted_roi or 0.0) for row in merged_rows]
        skipped_rois = [float(row.weighted_roi or 0.0) for row in skipped_enum]
        counted = (
            int(skips.skipped_buy_at_limit_up or 0)
            + int(skips.skipped_sell_at_limit_down or 0)
            + int(skips.skipped_stock_status or 0)
        )
        return {
            "enum_available": bool(enum_rows),
            "enum_count": len(enum_rows) if enum_rows else None,
            "price_book_count": len(book),
            "merged_count": len(merged_rows) if enum_rows else None,
            "skipped_buy_at_limit_up": int(skips.skipped_buy_at_limit_up or 0),
            "skipped_sell_at_limit_down": int(skips.skipped_sell_at_limit_down or 0),
            "skipped_stock_status": int(skips.skipped_stock_status or 0),
            "skipped_other": max(0, len(skipped) - counted),
            "book_mean_roi": _mean(book_rois),
            "merged_mean_roi": _mean(merged_rois) if enum_rows else None,
            "skipped_mean_roi": _mean(skipped_rois) if skipped_enum else None,
        }


def _is_book(row: PriceInvestmentRow) -> bool:
    return not str(row.skip_reason or "").strip()


def _is_completed(row: PriceInvestmentRow) -> bool:
    if not _is_book(row):
        return False
    lifecycle = str(row.lifecycle or "").strip().lower()
    if lifecycle in {"open", "holding", "active"} and not str(row.exit_date or "").strip():
        return False
    return bool(str(row.exit_date or "").strip()) or lifecycle == "complete"


def _profit(row: PriceInvestmentRow) -> float:
    return float(row.roi or 0.0)


def _year_key(raw: str) -> str:
    text = str(raw or "").strip()
    if len(text) >= 4 and text[:4].isdigit():
        return text[:4]
    return ""


def _share(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(float(part) / float(total), 4)


def _share_float(part: float, total: float) -> float:
    if abs(total) < 1e-12:
        return 0.0
    return round(float(part) / float(total), 4)


def _mean(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _profit_factor(wins: Sequence[float], losses: Sequence[float]) -> Optional[float]:
    loss_abs = abs(sum(losses))
    if loss_abs < 1e-12:
        return None
    return round(sum(wins) / loss_abs, 4)


def _win_rate_from_summary(summary: PriceOverallSummary) -> float:
    raw = float(summary.win_rate or 0.0)
    if raw > 1.0:
        return round(raw / 100.0, 4)
    return round(raw, 4)
