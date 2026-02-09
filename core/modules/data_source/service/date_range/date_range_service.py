"""
DateRangeService - 负责基于 renew 配置计算 last_update_map 和实体日期范围。

当前实现主要是对 DataSourceHandlerHelper 中现有逻辑的轻量封装，
为后续进一步对接 RenewManager / 各 renew services 预留统一入口。
"""
from typing import Any, Dict, Optional, Tuple

from core.modules.data_source.service.date_range import date_range_helper as drh


class DateRangeService:
    """统一的日期范围计算服务（Phase 1 + Phase 2）。"""

    def compute_last_update_map(self, context: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Phase 1：获取所有实体的“原始” last_update 映射（不考虑 renew_mode）。

        当前直接委托 date_range_helper.compute_last_update_map，
        后续可以在这里接入 RenewManager 等更复杂策略。
        """
        return drh.compute_last_update_map(context)

    def compute_entity_date_ranges(
        self,
        context: Dict[str, Any],
        last_update_map: Dict[str, Optional[str]],
    ) -> Dict[str, Tuple[str, str]]:
        """
        Phase 2：基于 last_update 映射 + renew_mode + renew_if_over_days，
        计算本次需要抓取的实体及其 (start_date, end_date)。

        当前直接委托 date_range_helper.compute_entity_date_ranges，
        方便后续在不改 Handler 的前提下切换到 RenewManager / 各 RenewService。
        """
        return drh.compute_entity_date_ranges(context, last_update_map)

