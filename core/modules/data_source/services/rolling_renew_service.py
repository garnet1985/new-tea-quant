"""
Rolling Renew Service

滚动刷新模式（rolling）的自动处理逻辑。
"""
from typing import Dict, Any, Tuple, Optional, Union
from loguru import logger

from core.global_enums.enums import TimeUnit
from core.utils.date.date_utils import DateUtils
from .base_renew_service import BaseRenewService


class RollingRenewService(BaseRenewService):
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
        
        # 如果 context 中已有日期范围，直接使用（统一返回单个日期范围）
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
        
        # 获取结束日期（所有股票统一使用 latest_completed_trading_date）
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if latest_completed_trading_date:
            if date_format == "day":
                end_date = latest_completed_trading_date
                end_value = DateUtils.get_current_period(latest_completed_trading_date, date_format)
            else:
                end_value = DateUtils.get_current_period(latest_completed_trading_date, date_format)
                end_date = DateUtils.format_period(end_value, date_format)
        else:
            current_date = DateUtils.get_current_date_str()
            end_value = DateUtils.get_current_period(current_date, date_format)
            end_date = DateUtils.format_period(end_value, date_format)
        
        # 计算 rolling 窗口的起始日期（从 end_value 前推 rolling_periods）
        rolling_start_value = DateUtils.subtract_periods(end_value, rolling_periods, date_format)
        rolling_start_date = DateUtils.format_period(rolling_start_value, date_format)
        
        # 从 context 中获取配置，判断是否需要按股票分组
        needs_stock_grouping = None
        if context:
            config = context.get("config")
            if config and hasattr(config, "get_needs_stock_grouping"):
                needs_stock_grouping = config.get_needs_stock_grouping()
        
        # 查询最新日期
        latest_dates_dict = self.query_latest_date(table_name, date_field, date_format, needs_stock_grouping)
        
        # 如果不需要分组（latest_dates_dict 为 None），返回单个日期范围
        if latest_dates_dict is None:
            # 不需要分组：查询整个表的最新日期
            if not self.data_manager:
                start_date, _ = self.get_default_date_range(date_format, context)
                return start_date, end_date
            
            try:
                model = self.data_manager.get_table(table_name)
                if model:
                    latest_record = model.load_one("1=1", order_by=f"{date_field} DESC")
                    if latest_record:
                        latest_value = latest_record.get(date_field)
                        if latest_value:
                            # 判断 latest_value 是否在 rolling 窗口内
                            period_diff = DateUtils.calculate_period_diff(latest_value, end_value, date_format)
                            if period_diff <= rolling_periods:
                                # 在窗口内：使用 rolling 窗口的起始日期
                                start_date = rolling_start_date
                                logger.info(f"滚动刷新（非分组）: {start_date} 至 {end_date}（数据库最新: {latest_value}，在窗口内）")
                            else:
                                # 不在窗口内：从最新日期开始追赶
                                start_value = DateUtils.add_one_period(latest_value, date_format)
                                start_date = DateUtils.format_period(start_value, date_format)
                                logger.info(f"滚动刷新（非分组）: {start_date} 至 {end_date}（数据库最新: {latest_value}，落后 {period_diff} 个周期）")
                            return start_date, end_date
            except Exception as e:
                logger.warning(f"查询非分组表最新日期失败: {e}")
            
            # 降级：使用默认日期范围
            start_date, _ = self.get_default_date_range(date_format, context)
            logger.info(f"数据库为空，使用默认日期范围: {start_date} 至 {end_date}")
            return start_date, end_date
        
        # 需要分组：为每个股票计算日期范围
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("需要按股票分组但 stock_list 为空，返回空字典")
            return {}
        
        # 获取默认起始日期（用于新股票）
        default_start_date, _ = self.get_default_date_range(date_format, context)
        
        # 为每个股票计算日期范围
        result = {}
        for stock_id in stock_list:
            stock_id_str = str(stock_id)
            latest_date = latest_dates_dict.get(stock_id_str)
            
            if latest_date:
                # 判断该股票的最后更新时间是否在 rolling 窗口内
                period_diff = DateUtils.calculate_period_diff(latest_date, end_value, date_format)
                if period_diff <= rolling_periods:
                    # 在窗口内：使用 rolling 窗口的起始日期
                    start_date = rolling_start_date
                    logger.debug(f"股票 {stock_id_str} 滚动刷新: {start_date} 至 {end_date}（数据库最新: {latest_date}，在窗口内）")
                else:
                    # 不在窗口内（落后太多）：起始日期 = 该股票最新日期的后一天
                    start_value = DateUtils.add_one_period(latest_date, date_format)
                    start_date = DateUtils.format_period(start_value, date_format)
                    logger.debug(f"股票 {stock_id_str} 滚动刷新: {start_date} 至 {end_date}（数据库最新: {latest_date}，落后 {period_diff} 个周期）")
            else:
                # 没找到（新股票）：使用系统默认起始时间
                start_date = default_start_date
                logger.debug(f"股票 {stock_id_str} 首次更新: {start_date} 至 {end_date}（新股票）")
            
            result[stock_id_str] = (start_date, end_date)
        
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
    
