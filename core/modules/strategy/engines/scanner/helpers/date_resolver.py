#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScanDateResolver:
    data_manager: any

    def resolve_scan_date(self, use_strict: bool) -> tuple[str, List[str]]:
        return self._resolve_strict_date() if use_strict else self._resolve_non_strict_date()

    def _resolve_strict_date(self) -> tuple[str, List[str]]:
        scan_date = (
            self.data_manager.service.calendar.get_real_world_latest_completed_trading_date()
        )
        if not scan_date:
            raise ValueError("failed to resolve strict scan date")
        stock_ids = self._get_stocks_with_kline(scan_date)
        if not stock_ids:
            raise ValueError(f"no kline data on {scan_date}")
        return scan_date, stock_ids

    def _resolve_non_strict_date(self) -> tuple[str, List[str]]:
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_db_latest_completed_trading_date,
        )

        scan_date = resolve_db_latest_completed_trading_date(self.data_manager)
        if not scan_date:
            raise ValueError("no trade calendar or daily kline anchor date in db")
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
