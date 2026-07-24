"""股票元数据加载工具。

本文件:
- StockMetaHelper: 单股 meta fallback 加载
  边界: 负责 DataManager.stock.list.load_meta 封装；不负责 sampling 或 contract 注入
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.modules.data_manager import DataManager

logger = logging.getLogger(__name__)


class StockMetaHelper:
    """加载单股 meta（entity / slice 共用）。"""

    @staticmethod
    def load(stock_id: str) -> Dict[str, Any]:
        fallback = {
            "id": stock_id,
            "name": stock_id,
            "industry": "",
            "type": "",
            "exchange_center": "",
            "delist_date": "",
        }
        try:
            row = DataManager().stock.list.load_meta(stock_id)
            if isinstance(row, dict) and row.get("id"):
                return {**fallback, **row}
        except Exception as exc:
            if str(stock_id).upper() != "DUMMY":
                logger.warning("加载股票元数据失败: stock_id=%s error=%s", stock_id, exc)
        return fallback


__all__ = ["StockMetaHelper"]
