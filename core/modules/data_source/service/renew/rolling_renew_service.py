"""
Rolling Renew Service

滚动刷新模式（rolling）的自动处理逻辑。
"""
from typing import Dict, Any, Tuple, Optional, Union
from loguru import logger

from core.global_enums.enums import TermType
from core.utils.date.date_utils import DateUtils
from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper


class RollingRenewService:
    """
    滚动刷新 Service
    
    逻辑（per stock）：
    1. 计算 rolling 窗口的起始日期（从 latest_completed_trading_date 前推 rolling_periods）
    2. 从数据库查询每个股票的最新日期（如果 needs_stock_grouping=True）
    3. 对于每个股票：
       - 如果该股票的最后更新时间在 rolling 窗口内：使用 rolling 窗口的起始日期
       - 如果该股票的最后更新时间不在 rolling 窗口内（落后太多）：起始日期 = 该股票最新日期的后一天
    4. 结束日期 = latest_completed_trading_date（所有股票统一）
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
        rolling_unit: str,
        rolling_length: int,
        table_name: str,
        date_field: str,
        context: Dict[str, Any] = None
    ) -> Union[Tuple[str, str], Dict[str, Tuple[str, str]]]:
        """
        计算滚动刷新的日期范围
        
        Args:
            date_format: 日期格式（quarter | month | day）
            rolling_unit: 滚动单位（quarter | month | day）
            rolling_length: 滚动长度（如 4 个季度、30 天）
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
        
        # 支持枚举和字符串两种格式（兼容性）
        if isinstance(date_format, TermType):
            date_format = date_format.value
        if isinstance(rolling_unit, TermType):
            rolling_unit = rolling_unit.value
        
        # 验证 rolling_unit 和 date_format 的一致性
        if date_format == TermType.QUARTERLY.value and rolling_unit != TermType.QUARTERLY.value:
            logger.warning(f"date_format='{TermType.QUARTERLY.value}' 但 rolling_unit='{rolling_unit}'，建议保持一致")
        elif date_format == TermType.MONTHLY.value and rolling_unit != TermType.MONTHLY.value:
            logger.warning(f"date_format='{TermType.MONTHLY.value}' 但 rolling_unit='{rolling_unit}'，建议保持一致")
        elif date_format == TermType.DAILY.value and rolling_unit != TermType.DAILY.value:
            logger.warning(f"date_format='{TermType.DAILY.value}' 但 rolling_unit='{rolling_unit}'，建议保持一致")
        
        # 将 rolling_unit 转换为 date_format 对应的周期数
        rolling_periods = self._convert_rolling_length_to_periods(
            rolling_unit, rolling_length, date_format
        )
        
        # 获取结束日期和end_value（用于计算rolling窗口）
        end_date = RenewCommonHelper.get_end_date(date_format, context)
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if latest_completed_trading_date:
            end_value = DateUtils.get_current_period(latest_completed_trading_date, date_format)
        else:
            current_date = DateUtils.get_current_date_str()
            end_value = DateUtils.get_current_period(current_date, date_format)
        
        # 计算 rolling 窗口的起始日期（从 end_value 前推 rolling_periods）
        rolling_start_value = DateUtils.subtract_periods(end_value, rolling_periods, date_format)
        rolling_start_date = DateUtils.format_period(rolling_start_value, date_format)
        
        # 获取是否需要分组
        needs_stock_grouping = RenewCommonHelper.get_needs_stock_grouping(context)
        
        # 查询最新日期
        latest_dates_dict = RenewCommonHelper.query_latest_date(
            self.data_manager, table_name, date_field, date_format, needs_stock_grouping
        )
        
        # 定义滚动模式的起始日期计算函数：判断是否在窗口内
        def _calculate_rolling_start(latest_value: str, end_date: str, date_format: str) -> str:
            period_diff = DateUtils.calculate_period_diff(latest_value, end_value, date_format)
            if period_diff <= rolling_periods:
                # 在窗口内：使用 rolling 窗口的起始日期
                return rolling_start_date
            else:
                # 不在窗口内：从最新日期开始追赶
                start_value = DateUtils.add_one_period(latest_value, date_format)
                return DateUtils.format_period(start_value, date_format)
        
        # 如果不需要分组，返回单个日期范围
        if latest_dates_dict is None:
            start_date, end_date = RenewCommonHelper.calculate_date_range_for_non_grouped(
                self.data_manager, table_name, date_field, date_format, end_date, context, _calculate_rolling_start
            )
            logger.info(f"滚动刷新（非分组）: {start_date} 至 {end_date}")
            return start_date, end_date
        
        # 需要分组：为每个股票计算日期范围
        result = RenewCommonHelper.calculate_date_range_for_grouped(
            latest_dates_dict, end_date, date_format, context, self.data_manager, _calculate_rolling_start
        )
        logger.info(f"滚动刷新（per stock）: 为 {len(result)} 只股票计算了日期范围")
        return result
    
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
        if isinstance(rolling_unit, TermType):
            rolling_unit = rolling_unit.value
        if isinstance(date_format, TermType):
            date_format = date_format.value
        
        if rolling_unit == TermType.QUARTERLY.value:
            if date_format == TermType.QUARTERLY.value:
                return rolling_length
            elif date_format == TermType.MONTHLY.value:
                # 将季度转换为月份（近似）
                return rolling_length * 3
            else:  # date_format == TermType.DAILY.value
                # 将季度转换为天数（近似）
                return rolling_length * 90
        elif rolling_unit == TermType.MONTHLY.value:
            if date_format == TermType.QUARTERLY.value:
                # 将月份转换为季度（向上取整）
                return (rolling_length + 2) // 3
            elif date_format == TermType.MONTHLY.value:
                return rolling_length
            else:  # date_format == TermType.DAILY.value
                # 将月份转换为天数（近似）
                return rolling_length * 30
        else:  # rolling_unit == TermType.DAILY.value
            if date_format == TermType.QUARTERLY.value:
                # 将天数转换为季度（近似）
                return (rolling_length + 90) // 90
            elif date_format == TermType.MONTHLY.value:
                # 将天数转换为月份（近似）
                return (rolling_length + 30) // 30
            else:  # date_format == TermType.DAILY.value
                return rolling_length
    
