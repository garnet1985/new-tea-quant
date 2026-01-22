"""
Incremental Renew Service

增量更新模式（incremental）的自动处理逻辑。
"""
from typing import Dict, Any, Tuple, Optional, Union
from loguru import logger

from core.utils.date.date_utils import DateUtils
from .base_renew_service import BaseRenewService


class IncrementalRenewService(BaseRenewService):
    """
    增量更新 Service
    
    逻辑（per stock）：
    1. 从数据库查询每个股票的最新日期（如果 needs_stock_grouping=True）
    2. 对于每个股票：
       - 如果找到了该股票的最新日期：起始日期 = 该股票最新日期的后一天
       - 如果没找到（新股票）：起始日期 = 系统默认起始时间
    3. 结束日期 = latest_completed_trading_date（所有股票统一）
    """
    
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
        
        # 如果 context 中已有日期范围，直接使用（统一返回单个日期范围）
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return context["start_date"], context["end_date"]
        
        # 获取当前日期/季度/月份
        current_date = DateUtils.get_current_date_str()
        current_value = DateUtils.get_current_period(current_date, date_format)
        
        # 获取结束日期（所有股票统一使用 latest_completed_trading_date）
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if latest_completed_trading_date:
            if date_format == "day":
                end_date = latest_completed_trading_date
            else:
                end_date = DateUtils.format_period(
                    DateUtils.get_current_period(latest_completed_trading_date, date_format),
                    date_format
                )
        else:
            end_date = DateUtils.format_period(current_value, date_format)
        
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
                            start_value = DateUtils.add_one_period(latest_value, date_format)
                            start_date = DateUtils.format_period(start_value, date_format)
                            logger.info(f"增量更新（非分组）: {start_date} 至 {end_date}（数据库最新: {latest_value}）")
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
                # 找到了该股票的最新日期：起始日期 = 该股票最新日期的后一天
                start_value = DateUtils.add_one_period(latest_date, date_format)
                start_date = DateUtils.format_period(start_value, date_format)
                logger.debug(f"股票 {stock_id_str} 增量更新: {start_date} 至 {end_date}（数据库最新: {latest_date}）")
            else:
                # 没找到（新股票）：使用系统默认起始时间
                start_date = default_start_date
                logger.debug(f"股票 {stock_id_str} 首次更新: {start_date} 至 {end_date}（新股票）")
            
            result[stock_id_str] = (start_date, end_date)
        
        logger.info(f"增量更新（per stock）: 为 {len(result)} 只股票计算了日期范围")
        return result
