"""
Refresh Renew Service

全量刷新模式（refresh）的自动处理逻辑。
"""
from typing import Dict, Any, Tuple
from loguru import logger

from core.utils.date.date_utils import DateUtils
from .base_renew_service import BaseRenewService


class RefreshRenewService(BaseRenewService):
    """
    全量刷新 Service
    
    逻辑：
    1. 使用 default_date_range 计算日期范围
    2. 如果 default_date_range 为空，使用默认日期范围（从系统默认时间到最近完成的交易日）
    """
    
    def calculate_date_range(
        self,
        date_format: str,
        default_date_range: Dict[str, int],
        context: Dict[str, Any] = None
    ) -> Tuple[str, str]:
        """
        计算全量刷新的日期范围
        
        Args:
            date_format: 日期格式（quarter | month | day）
            default_date_range: 默认日期范围配置（如 {"years": 5}）
            context: 执行上下文
        
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return context["start_date"], context["end_date"]
        
        # 如果 default_date_range 为空，使用默认日期范围（从系统默认时间到最近完成的交易日）
        if not default_date_range:
            start_date, end_date = self.get_default_date_range(date_format, context)
            logger.info(f"全量刷新: {start_date} 至 {end_date}（无 default_date_range，使用系统默认）")
            return start_date, end_date
        
        # 使用 default_date_range 计算日期范围
        current_date = DateUtils.get_current_date_str()
        start_date, end_date = self._calculate_date_range_from_config(
            current_date, date_format, default_date_range, context
        )
        logger.info(f"全量刷新: {start_date} 至 {end_date}（使用 default_date_range）")
        
        return start_date, end_date
    
    def _calculate_date_range_from_config(
        self,
        current_date: str,
        date_format: str,
        default_date_range: Dict[str, int],
        context: Dict[str, Any] = None
    ) -> Tuple[str, str]:
        """
        根据 default_date_range 配置计算日期范围
        
        Args:
            current_date: 当前日期（YYYYMMDD）
            date_format: 日期格式（quarter | month | day）
            default_date_range: 日期范围配置（如 {"years": 5}）
            context: 执行上下文（可能包含 latest_completed_trading_date）
        
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        context = context or {}
        
        # 获取当前周期值
        current_value = DateUtils.get_current_period(current_date, date_format)
        
        # 获取结束日期（优先使用 latest_completed_trading_date）
        if date_format == "day":
            latest_completed_trading_date = context.get("latest_completed_trading_date")
            if latest_completed_trading_date:
                end_date = latest_completed_trading_date
            else:
                end_date = current_date
        else:
            end_date = DateUtils.format_period(current_value, date_format)
        
        # 计算开始日期（业务逻辑：根据 default_date_range 配置）
        if date_format == "quarter":
            current_year, current_quarter = current_value
            if "years" in default_date_range:
                years = default_date_range["years"]
                start_year = current_year - years
                start_quarter = 1
            elif "quarters" in default_date_range:
                quarters = default_date_range["quarters"]
                start_year = current_year
                start_quarter = current_quarter - quarters + 1
                while start_quarter < 1:
                    start_quarter += 4
                    start_year -= 1
            else:
                # 默认 5 年
                start_year = current_year - 5
                start_quarter = 1
            start_date = f"{start_year}Q{start_quarter}"
        elif date_format == "month":
            current_year, current_month = current_value
            if "years" in default_date_range:
                years = default_date_range["years"]
                start_year = current_year - years
                start_month = 1
            elif "months" in default_date_range:
                months = default_date_range["months"]
                start_year = current_year
                start_month = current_month - months + 1
                while start_month < 1:
                    start_month += 12
                    start_year -= 1
            else:
                # 默认 3 年
                start_year = current_year - 3
                start_month = 1
            start_date = f"{start_year}{start_month:02d}"
        else:  # date_format == "day"
            if "years" in default_date_range:
                years = default_date_range["years"]
                start_date = DateUtils.get_date_before_days(end_date, years * 365)
            elif "days" in default_date_range:
                days = default_date_range["days"]
                start_date = DateUtils.get_date_before_days(end_date, days)
            else:
                # 默认 5 年
                start_date = DateUtils.get_date_before_days(end_date, 5 * 365)
        
        return start_date, end_date
