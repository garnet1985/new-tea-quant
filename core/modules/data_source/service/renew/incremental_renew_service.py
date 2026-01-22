"""
Incremental Renew Service

增量更新模式（incremental）的自动处理逻辑。
"""
from typing import Dict, Any, Tuple, Optional, Union
from loguru import logger

from core.utils.date.date_utils import DateUtils
from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper


class IncrementalRenewService:
    """
    增量更新 Service
    
    逻辑（per stock）：
    1. 从数据库查询每个股票的最新日期（如果 needs_stock_grouping=True）
    2. 对于每个股票：
       - 如果找到了该股票的最新日期：起始日期 = 该股票最新日期的后一天
       - 如果没找到（新股票）：起始日期 = 系统默认起始时间
    3. 结束日期 = latest_completed_trading_date（所有股票统一）
    """
    
    def __init__(self, data_manager=None):
        """
        初始化 Service
        
        Args:
            data_manager: DataManager 实例（用于查询数据库）
        """
        self.data_manager = data_manager
    
    def calculate_date_range(
        self,
        date_format: str,
        table_name: str,
        date_field: str,
        context: Dict[str, Any] = None
    ) -> Union[Tuple[str, str], Dict[str, Tuple[str, str]]]:
        """
        计算增量更新的日期范围
        
        Args:
            date_format: 日期格式（quarter | month | day）
            table_name: 数据库表名
            date_field: 日期字段名
            context: 执行上下文（包含 stock_list, latest_completed_trading_date 等）
        
        Returns:
            - 如果需要按股票分组：Dict[str, Tuple[str, str]] {stock_id: (start_date, end_date)}
            - 如果不需要分组：Tuple[str, str] (start_date, end_date)
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return context["start_date"], context["end_date"]
        
        # 获取结束日期
        end_date = RenewCommonHelper.get_end_date(date_format, context)
        
        # 获取是否需要分组
        needs_stock_grouping = RenewCommonHelper.get_needs_stock_grouping(context)
        
        # 查询最新日期
        latest_dates_dict = RenewCommonHelper.query_latest_date(
            self.data_manager, table_name, date_field, date_format, needs_stock_grouping
        )
        
        # 定义增量模式的起始日期计算函数：最新日期的后一个周期
        def _calculate_incremental_start(latest_value: str, end_date: str, date_format: str) -> str:
            start_value = DateUtils.add_one_period(latest_value, date_format)
            return DateUtils.format_period(start_value, date_format)
        
        # 如果不需要分组，返回单个日期范围
        if latest_dates_dict is None:
            start_date, end_date = RenewCommonHelper.calculate_date_range_for_non_grouped(
                self.data_manager, table_name, date_field, date_format, end_date, context, _calculate_incremental_start
            )
            logger.info(f"增量更新（非分组）: {start_date} 至 {end_date}")
            return start_date, end_date
        
        # 需要分组：为每个股票计算日期范围
        result = RenewCommonHelper.calculate_date_range_for_grouped(
            latest_dates_dict, end_date, date_format, context, self.data_manager, _calculate_incremental_start
        )
        logger.info(f"增量更新（per stock）: 为 {len(result)} 只股票计算了日期范围")
        return result
