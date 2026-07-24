"""价格回测：按需加载单股日 K 线。

本文件:
- load_stock_klines: DataManager qfq daily
  边界: 负责 K 线 IO；不负责 slippage 或成交回放
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def load_stock_klines(
    stock_id: str,
    *,
    start_date: str,
    end_date: str,
    term: str = "daily",
) -> List[Dict[str, Any]]:
    """从 DataManager 拉 qfq daily；失败返回空列表。"""
    sid = str(stock_id or "").strip()
    start = str(start_date or "").strip()
    end = str(end_date or "").strip()
    if not sid or not start or not end:
        return []
    try:
        from core.modules.data_manager import DataManager

        rows = DataManager().stock.kline.load_qfq_split(
            sid,
            term=term,
            start_date=start,
            end_date=end,
        )
        return list(rows or [])
    except Exception as exc:
        logger.warning(
            "load_stock_klines 失败: stock_id=%s %s..%s error=%s",
            sid,
            start,
            end,
            exc,
        )
        return []


__all__ = ["load_stock_klines"]
