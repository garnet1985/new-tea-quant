"""
Base Renew Service

所有 renew service 的基类，提供公共逻辑。
"""
from typing import Dict, Any, Tuple, Optional
from loguru import logger

from core.global_enums.enums import TimeUnit
from core.utils.date.date_utils import DateUtils
from core.infra.project_context import ConfigManager


class BaseRenewService:
    """
    Renew Service 基类
    
    提供公共逻辑：
    - 数据库为空时，从系统默认时间开始到最近完成的交易日
    """
    
    def __init__(self, data_manager=None):
        """
        初始化 Service
        
        Args:
            data_manager: DataManager 实例（用于查询数据库）
        """
        self.data_manager = data_manager
    
    def get_default_date_range(self, date_format: str, context: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        获取默认日期范围（数据库为空时使用）
        
        公共逻辑：从系统默认时间开始到最近完成的交易日
        
        Args:
            date_format: 日期格式（quarter | month | day）
            context: 执行上下文（可能包含 latest_completed_trading_date）
        
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        context = context or {}
        
        # 获取系统默认开始日期
        default_start_date = ConfigManager.get_default_start_date()
        
        # 获取最近完成的交易日（优先从 context 读取）
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date and self.data_manager:
            try:
                latest_completed_trading_date = self.data_manager.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新交易日失败: {e}，使用当前日期")
                latest_completed_trading_date = DateUtils.get_current_date_str()
        
        if not latest_completed_trading_date:
            latest_completed_trading_date = DateUtils.get_current_date_str()
        
        # 根据 date_format 转换日期格式
        start_date = self._convert_date_to_format(default_start_date, date_format)
        end_date = self._convert_date_to_format(latest_completed_trading_date, date_format)
        
        return start_date, end_date
    
    def _convert_date_to_format(self, date_str: str, date_format: str) -> str:
        """
        将日期字符串转换为指定格式
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            date_format: 目标格式（quarter | month | day）
        
        Returns:
            转换后的日期字符串
        """
        # 支持枚举和字符串两种格式（兼容性）
        if isinstance(date_format, TimeUnit):
            date_format = date_format.value
        
        if date_format == TimeUnit.QUARTER.value:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            if month <= 3:
                quarter = 1
            elif month <= 6:
                quarter = 2
            elif month <= 9:
                quarter = 3
            else:
                quarter = 4
            return f"{year}Q{quarter}"
        elif date_format == TimeUnit.MONTH.value:
            return date_str[:6]  # YYYYMM
        else:  # date_format == TimeUnit.DAY.value
            return date_str  # YYYYMMDD
    
    def query_latest_date(
        self, 
        table_name: str, 
        date_field: str, 
        date_format: str
    ) -> Optional[str]:
        """
        查询数据库最新日期（公共方法）
        
        Args:
            table_name: 数据库表名
            date_field: 日期字段名
            date_format: 日期格式（用于验证）
        
        Returns:
            最新日期字符串，如果表为空返回 None
        """
        if not self.data_manager:
            return None
        
        try:
            model = self.data_manager.get_table(table_name)
            if model:
                latest_record = model.load_latest()
                if latest_record:
                    return latest_record.get(date_field, '')
        except Exception as e:
            logger.warning(f"查询数据库失败 {table_name}.{date_field}: {e}")
        
        return None
