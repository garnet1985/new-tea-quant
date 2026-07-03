#!/usr/bin/env python3
"""回测日期解析辅助函数。"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def resolve_latest_completed_trading_date(data_manager: Any) -> str:
    """获取最新已完成交易日。

    Args:
        data_manager: DataManager 实例

    Returns:
        latest_completed_trading_date（日期字符串，例如 "20240101")

    设计：
    - 使用 DataManager.calendar_service.get_latest_completed_trading_date()
    - 全系统 latest completed 统一读入口
    - 简单日期字符串，不适合作为 contract
    """
    try:
        cal_svc = data_manager.service.calendar
        if cal_svc is None:
            logger.warning("DataManager.calendar_service 为 None，返回空字符串")
            return ""
        
        latest_date = cal_svc.get_latest_completed_trading_date()
        return str(latest_date or "").strip()
        
    except Exception as e:
        logger.error(f"获取最新已完成交易日失败：{e}", exc_info=True)
        return ""


__all__ = ["resolve_latest_completed_trading_date"]