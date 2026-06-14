#!/usr/bin/env python3
"""价格回测 worker 按需加载单股 K 线。"""

from __future__ import annotations

from typing import Any, Dict, List


def load_stock_klines(
    stock_id: str,
    *,
    start_date: str,
    end_date: str,
    term: str = "daily",
) -> List[Dict[str, Any]]:
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
    )

    bootstrap_strategy_worker_data_manager()
    from core.modules.data_manager import DataManager

    dm = DataManager.get_instance()
    if dm is None:
        return []
    svc = dm.stock.kline
    rows = svc.load_qfq_split(
        stock_id,
        term=term,
        start_date=str(start_date or "").strip(),
        end_date=str(end_date or "").strip(),
    )
    return list(rows or [])


__all__ = ["load_stock_klines"]
