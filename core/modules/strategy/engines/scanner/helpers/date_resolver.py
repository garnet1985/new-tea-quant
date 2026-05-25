#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScanDateResolver:
    data_manager: any

    @staticmethod
    def resolve_anchor_date(data_manager, *, use_strict: bool) -> str:
        """
        扫描截止日锚点。

        - 严格模式：real-world（新浪/东财 K 线，不读 ``sys_trade_calendar``）
        - 非严格模式：``CalendarService.get_latest_completed_trading_date()``
        """
        cal_svc = getattr(getattr(data_manager, "service", None), "calendar", None)
        if cal_svc is None:
            return ""
        try:
            if use_strict:
                return str(
                    cal_svc.get_real_world_latest_completed_trading_date() or ""
                ).strip()
            return str(cal_svc.get_latest_completed_trading_date() or "").strip()
        except Exception as exc:
            logger.debug("resolve_anchor_date failed use_strict=%s: %s", use_strict, exc)
            return ""

    def resolve_scan_date(self, use_strict: bool) -> tuple[str, List[str]]:
        return self._resolve_strict_date() if use_strict else self._resolve_non_strict_date()

    def _resolve_strict_date(self) -> tuple[str, List[str]]:
        scan_date = self.resolve_anchor_date(self.data_manager, use_strict=True)
        if not scan_date:
            raise ValueError("failed to resolve strict scan date (real-world)")
        stock_ids = self._get_stocks_with_kline(scan_date)
        if not stock_ids:
            raise ValueError(f"no kline data on {scan_date}")
        return scan_date, stock_ids

    def _resolve_non_strict_date(self) -> tuple[str, List[str]]:
        scan_date = self.resolve_anchor_date(self.data_manager, use_strict=False)
        if not scan_date:
            raise ValueError("failed to resolve non-strict scan date (calendar service)")
        stock_ids = self._get_stocks_with_kline(scan_date)
        if not stock_ids:
            raise ValueError(f"no kline data on {scan_date}")
        return scan_date, stock_ids

    def _get_stocks_with_kline(self, date: str) -> List[str]:
        kline_model = self.data_manager.get_table("sys_stock_klines")
        if not kline_model:
            return []
        klines = kline_model.load_by_date(date)
        stock_ids = list(set([k["id"] for k in klines if k.get("id")]))
        return sorted(stock_ids)


__all__ = ["ScanDateResolver"]
