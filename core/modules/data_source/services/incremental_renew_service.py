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
        current_value = self._get_current_value_for_format(current_date, date_format)
        
        # 从数据库查询最新日期
        latest_value = self.query_latest_date(table_name, date_field, date_format)
        
        # 计算日期范围
        if not latest_value:
            # 数据库为空：使用默认日期范围（从系统默认时间到最近完成的交易日）
            start_date, end_date = self.get_default_date_range(date_format, context)
            logger.info(f"数据库为空，使用默认日期范围: {start_date} 至 {end_date}")
        else:
            # 数据库不为空：从最新日期到当前
            start_value = self._add_one_period_for_format(latest_value, date_format)
            start_date = self._format_value_for_format(start_value, date_format)
            end_date = self._format_value_for_format(current_value, date_format)
            logger.info(f"增量更新: {start_date} 至 {end_date}（数据库最新: {latest_value}）")
        
        return start_date, end_date
    
    def _get_current_value_for_format(self, current_date: str, date_format: str):
        """根据 date_format 获取当前值"""
        if date_format == "quarter":
            current_year = int(current_date[:4])
            current_month = int(current_date[4:6])
            if current_month <= 3:
                return (current_year, 1)
            elif current_month <= 6:
                return (current_year, 2)
            elif current_month <= 9:
                return (current_year, 3)
            else:
                return (current_year, 4)
        elif date_format == "month":
            return (int(current_date[:4]), int(current_date[4:6]))
        else:  # date_format == "day"
            return current_date
    
    def _parse_value_for_format(self, value: str, date_format: str):
        """解析日期值"""
        if date_format == "quarter":
            year = int(value[:4])
            quarter = int(value[5])
            return (year, quarter)
        elif date_format == "month":
            return (int(value[:4]), int(value[4:6]))
        else:  # date_format == "day"
            return value
    
    def _format_value_for_format(self, value, date_format: str) -> str:
        """格式化日期值"""
        if date_format == "quarter":
            year, quarter = value
            return f"{year}Q{quarter}"
        elif date_format == "month":
            year, month = value
            return f"{year}{month:02d}"
        else:  # date_format == "day"
            return value
    
    def _add_one_period_for_format(self, latest_value: str, date_format: str):
        """添加一个周期（用于历史追赶）"""
        from datetime import timedelta
        
        latest = self._parse_value_for_format(latest_value, date_format)
        
        if date_format == "quarter":
            year, quarter = latest
            quarter += 1
            if quarter > 4:
                quarter = 1
                year += 1
            return (year, quarter)
        elif date_format == "month":
            year, month = latest
            month += 1
            if month > 12:
                month = 1
                year += 1
            return (year, month)
        else:  # date_format == "day"
            date = DateUtils.parse_yyyymmdd(latest)
            new_date = date + timedelta(days=1)
            return DateUtils.format_to_yyyymmdd(new_date)
