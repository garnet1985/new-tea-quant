"""
Incremental Renew Service

增量更新模式（incremental）的自动处理逻辑。
"""
from typing import Dict, Any, Tuple, Optional
from loguru import logger

from core.utils.date.date_utils import DateUtils
from .base_renew_service import BaseRenewService


class IncrementalRenewService(BaseRenewService):
    """
    增量更新 Service
    
    逻辑：
    1. 从数据库查询最新日期
    2. 如果数据库为空，使用默认日期范围（从系统默认时间到最近完成的交易日）
    3. 否则，从最新日期到当前
    """
    
    def calculate_date_range(
        self,
        date_format: str,
        table_name: str,
        date_field: str,
        context: Dict[str, Any] = None
    ) -> Tuple[str, str]:
        """
        计算增量更新的日期范围
        
        Args:
            date_format: 日期格式（quarter | month | day）
            table_name: 数据库表名
            date_field: 日期字段名
            context: 执行上下文
        
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return context["start_date"], context["end_date"]
        
        # 获取当前日期/季度/月份
        current_date = DateUtils.get_current_date_str()
        current_value = DateUtils.get_current_period(current_date, date_format)
        
        # 从数据库查询最新日期
        latest_value = self.query_latest_date(table_name, date_field, date_format)
        
        # 计算日期范围
        if not latest_value:
            # 数据库为空：使用默认日期范围（从系统默认时间到最近完成的交易日）
            start_date, end_date = self.get_default_date_range(date_format, context)
            logger.info(f"数据库为空，使用默认日期范围: {start_date} 至 {end_date}")
        else:
            # 数据库不为空：从最新日期到当前
            start_value = DateUtils.add_one_period(latest_value, date_format)
            start_date = DateUtils.format_period(start_value, date_format)
            end_date = DateUtils.format_period(current_value, date_format)
            logger.info(f"增量更新: {start_date} 至 {end_date}（数据库最新: {latest_value}）")
        
        return start_date, end_date
