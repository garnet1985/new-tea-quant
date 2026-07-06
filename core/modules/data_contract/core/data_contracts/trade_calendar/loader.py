"""TradeCalendar Loader。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader

logger = logging.getLogger(__name__)


class TradeCalendarLoader(BaseDataContractLoader):
    """交易日历 Loader（从 DataManager 加载交易日历）。"""

    def load(
        self,
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """加载交易日历数据。

        Args:
            params: 加载参数（包含 start/end）
            context: 可选上下文信息

        Returns:
            交易日历列表（包含 date、is_open 等字段）

        设计：
        - 使用 DataManager.service.calendar.get_trade_calendar()
        - 返回交易日历列表（每个元素包含 date、is_open 等字段）
        - GLOBAL scope（全局共享）
        - TIME_SERIES type（时序数据）
        """
        start = params.get("start")
        end = params.get("end")

        try:
            from core.modules.data_manager import DataManager

            data_mgr = DataManager(is_verbose=False)
            cal_svc = data_mgr.service.calendar

            # 获取交易日历
            trade_calendar = cal_svc.get_trade_calendar(
                start_date=str(start) if start else None,
                end_date=str(end) if end else None,
            )

            # 转换为标准格式
            result = []
            for date_str in trade_calendar:
                result.append({
                    "date": date_str,
                    "is_open": True,  # 交易日历中的日期都是交易日
                })

            logger.info(
                f"TradeCalendarLoader.load() 成功：start={start}, end={end}, "
                f"数据量={len(result)}"
            )

            return result

        except Exception as e:
            logger.error(
                f"TradeCalendarLoader.load() 失败：start={start}, end={end}, "
                f"error={e}",
                exc_info=True
            )
            return []

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """批量加载交易日历数据（GLOBAL scope 不需要 batch）。

        Args:
            entity_ids: Entity ID 列表（GLOBAL scope 不使用）
            params: 加载参数（包含 start/end）
            context: 可选上下文信息

        Returns:
            Dict[str, List[Dict[str, Any]]]（GLOBAL scope 返回 {"global": data}）

        设计：
        - GLOBAL scope 不需要 entity_ids
        - 返回 {"global": trade_calendar_data}
        """
        # GLOBAL scope，entity_ids 不使用
        data = self.load(params, context)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}