"""
Rolling Renew Service

滚动刷新模式（rolling）的自动处理逻辑。
"""
from typing import Dict, Any, Tuple, Optional
from loguru import logger

from core.global_enums.enums import TimeUnit
from core.utils.date.date_utils import DateUtils
from .base_renew_service import BaseRenewService


class RollingRenewService(BaseRenewService):
    """
    滚动刷新 Service
    
    逻辑：
    1. 使用 rolling_unit 和 rolling_length 计算滚动窗口
    2. 如果数据库为空，使用默认日期范围（从系统默认时间到最近完成的交易日）
    3. 否则，滚动刷新最近 N 个时间单位
    """
    
    def calculate_date_range(
        self,
        date_format: str,
        rolling_unit: str,
        rolling_length: int,
        table_name: str,
        date_field: str,
        context: Dict[str, Any] = None
    ) -> Tuple[str, str]:
        """
        计算滚动刷新的日期范围
        
        Args:
            date_format: 日期格式（quarter | month | day）
            rolling_unit: 滚动单位（quarter | month | day）
            rolling_length: 滚动长度（如 4 个季度、30 天）
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
        
        # 支持枚举和字符串两种格式（兼容性）
        if isinstance(date_format, TimeUnit):
            date_format = date_format.value
        if isinstance(rolling_unit, TimeUnit):
            rolling_unit = rolling_unit.value
        
        # 验证 rolling_unit 和 date_format 的一致性
        if date_format == TimeUnit.QUARTER.value and rolling_unit != TimeUnit.QUARTER.value:
            logger.warning(f"date_format='{TimeUnit.QUARTER.value}' 但 rolling_unit='{rolling_unit}'，建议保持一致")
        elif date_format == TimeUnit.MONTH.value and rolling_unit != TimeUnit.MONTH.value:
            logger.warning(f"date_format='{TimeUnit.MONTH.value}' 但 rolling_unit='{rolling_unit}'，建议保持一致")
        elif date_format == TimeUnit.DAY.value and rolling_unit != TimeUnit.DAY.value:
            logger.warning(f"date_format='{TimeUnit.DAY.value}' 但 rolling_unit='{rolling_unit}'，建议保持一致")
        
        # 将 rolling_unit 转换为 date_format 对应的周期数
        rolling_periods = self._convert_rolling_length_to_periods(
            rolling_unit, rolling_length, date_format
        )
        
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
            # 数据库不为空：计算时间间隔
            period_diff = DateUtils.calculate_period_diff(
                latest_value, current_value, date_format
            )
            
            if period_diff <= rolling_periods:
                # 间隔 <= rolling_periods：滚动刷新最近 rolling_periods 个时间单位
                start_value = DateUtils.subtract_periods(
                    current_value, rolling_periods, date_format
                )
                start_date = DateUtils.format_period(start_value, date_format)
                end_date = DateUtils.format_period(current_value, date_format)
                period_unit = DateUtils.get_period_unit(date_format)
                logger.info(f"滚动刷新最近 {rolling_periods} 个{period_unit}: {start_date} 至 {end_date}（数据库最新: {latest_value}）")
            else:
                # 间隔 > rolling_periods：从最新日期开始追赶
                start_value = DateUtils.add_one_period(latest_value, date_format)
                start_date = DateUtils.format_period(start_value, date_format)
                end_date = DateUtils.format_period(current_value, date_format)
                period_unit = DateUtils.get_period_unit(date_format)
                logger.info(f"历史追赶: {start_date} 至 {end_date}（数据库最新: {latest_value}，落后 {period_diff} 个{period_unit}）")
        
        return start_date, end_date
    
    def _convert_rolling_length_to_periods(
        self, 
        rolling_unit: str, 
        rolling_length: int, 
        date_format: str
    ) -> int:
        """
        将 rolling_unit 和 rolling_length 转换为 date_format 对应的周期数
        
        Args:
            rolling_unit: 滚动单位（quarter | month | day）
            rolling_length: 滚动长度
            date_format: 日期格式（quarter | month | day）
        
        Returns:
            周期数
        """
        # 支持枚举和字符串两种格式（兼容性）
        if isinstance(rolling_unit, TimeUnit):
            rolling_unit = rolling_unit.value
        if isinstance(date_format, TimeUnit):
            date_format = date_format.value
        
        if rolling_unit == TimeUnit.QUARTER.value:
            if date_format == TimeUnit.QUARTER.value:
                return rolling_length
            elif date_format == TimeUnit.MONTH.value:
                # 将季度转换为月份（近似）
                return rolling_length * 3
            else:  # date_format == TimeUnit.DAY.value
                # 将季度转换为天数（近似）
                return rolling_length * 90
        elif rolling_unit == TimeUnit.MONTH.value:
            if date_format == TimeUnit.QUARTER.value:
                # 将月份转换为季度（向上取整）
                return (rolling_length + 2) // 3
            elif date_format == TimeUnit.MONTH.value:
                return rolling_length
            else:  # date_format == TimeUnit.DAY.value
                # 将月份转换为天数（近似）
                return rolling_length * 30
        else:  # rolling_unit == TimeUnit.DAY.value
            if date_format == TimeUnit.QUARTER.value:
                # 将天数转换为季度（近似）
                return (rolling_length + 90) // 90
            elif date_format == TimeUnit.MONTH.value:
                # 将天数转换为月份（近似）
                return (rolling_length + 30) // 30
            else:  # date_format == TimeUnit.DAY.value
                return rolling_length
    
