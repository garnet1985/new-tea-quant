"""扫描日锚点与当日有 K 线的股票宇宙。"""

from __future__ import annotations

import logging
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)


class ScanDateResolver:
    """解析 scan_date + universe（当日有日 K 的股票）。"""

    def __init__(self, data_manager: Any) -> None:
        self.data_manager = data_manager

    @staticmethod
    def load_kline_latest_date(data_manager: Any) -> str:
        stock = getattr(data_manager, "stock", None)
        if stock is None:
            return ""
        loader = getattr(getattr(stock, "kline", None), "load_latest_date", None)
        if not callable(loader):
            return ""
        try:
            return str(loader("daily") or "").strip()
        except Exception as exc:
            logger.debug("load kline latest date failed: %s", exc)
            return ""

    @staticmethod
    def resolve_anchor_date(data_manager: Any, *, use_strict: bool) -> str:
        """严格：real-world 上一完整交易日；非严格：freshness 截至日（并 clamp 到 K 线最新）。"""
        cal_svc = getattr(getattr(data_manager, "service", None), "calendar", None)
        if cal_svc is None:
            return ""
        try:
            if use_strict:
                return str(
                    cal_svc.get_real_world_latest_completed_trading_date() or ""
                ).strip()
            from core.modules.data_source.catalog.freshness_probe import (
                _resolve_freshness_end_date,
            )

            anchor = str(_resolve_freshness_end_date(data_manager) or "").strip()
        except Exception as exc:
            logger.debug("resolve_anchor_date failed use_strict=%s: %s", use_strict, exc)
            return ""

        if not anchor:
            return ""

        kline_latest = ScanDateResolver.load_kline_latest_date(data_manager)
        if kline_latest and anchor > kline_latest:
            logger.warning(
                "扫描锚点 %s 晚于库内 K 线最新日 %s，按 %s 执行扫描",
                anchor,
                kline_latest,
                kline_latest,
            )
            return kline_latest
        return anchor

    def resolve_scan_date(self, *, use_strict: bool) -> Tuple[str, List[str]]:
        scan_date = self.resolve_anchor_date(self.data_manager, use_strict=use_strict)
        if not scan_date:
            raise ValueError(
                "failed to resolve scan date "
                f"({'strict/real-world' if use_strict else 'non-strict/freshness'})"
            )
        stock_ids = self.stocks_with_kline(scan_date)
        if not stock_ids:
            raise ValueError(f"no kline data on {scan_date}")
        return scan_date, stock_ids

    def stocks_with_kline(self, date: str) -> List[str]:
        get_table = getattr(self.data_manager, "get_table", None)
        if not callable(get_table):
            return []
        kline_model = get_table("sys_stock_klines")
        if not kline_model:
            return []
        rows = kline_model.load_by_date(date)
        ids = {
            str(row.get("id") or "").strip()
            for row in (rows or [])
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        return sorted(ids)


__all__ = ["ScanDateResolver"]
