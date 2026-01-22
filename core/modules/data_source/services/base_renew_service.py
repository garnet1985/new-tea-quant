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
        date_format: str,
        needs_stock_grouping: Optional[bool] = None
    ) -> Optional[Dict[str, str]]:
        """
        查询数据库最新日期（公共方法）
        
        逻辑：
        1. 通过 DataManager.get_table() 获取表的 model
        2. 根据配置或表的主键结构判断是否需要按股票分组：
           - 如果配置中显式声明了 needs_stock_grouping，使用配置值
           - 否则，根据主键结构自动判断（主键中除了日期字段还有其他字段 = 需要分组）
        3. 根据是否需要分组，查询最新日期：
           - 不需要分组（如 GDP, LPR）：返回 None（表示整个表的最新日期，在调用方处理）
           - 需要分组（如 stock_kline）：返回 {stock_id: latest_date} 字典
        
        Args:
            table_name: 数据库表名
            date_field: 日期字段名（表里声明的日期字段）
            date_format: 日期格式（用于验证）
            needs_stock_grouping: 是否需要按股票分组（None 表示自动判断）
        
        Returns:
            - 如果需要分组：Dict[str, str] {stock_id: latest_date}，如果表为空返回 None
            - 如果不需要分组：返回 None（调用方需要单独处理）
        """
        if not self.data_manager:
            return None
        
        try:
            # 步骤 1：通过 DataManager 获取 model（内部方法，仅供 service 使用）
            model = self.data_manager.get_table(table_name)
            if not model:
                return None
            
            # 步骤 2：判断是否需要分组（优先级：配置 > 自动判断）
            if needs_stock_grouping is None:
                # 如果未配置，根据主键结构自动判断
                try:
                    primary_keys = model._get_primary_keys_from_schema()
                    # 过滤掉日期字段，得到分组键
                    group_keys = [k for k in primary_keys if k != date_field]
                    needs_grouping = len(group_keys) > 0
                except Exception:
                    # 如果无法获取主键，默认需要分组（保守策略）
                    needs_grouping = True
            else:
                needs_grouping = needs_stock_grouping
            
            # 步骤 3：根据是否需要分组，查询最新日期
            if not needs_grouping:
                # 不需要分组：返回 None，调用方需要单独处理（查询整个表的最新日期）
                return None
            
            # 需要分组：查询每个股票的最新日期
            try:
                latest_records = model.load_latest_records(date_field=date_field)
                if not latest_records:
                    return None
                
                # 构建 {stock_id: latest_date} 字典
                # 假设主键中除了日期字段的第一个字段是 stock_id（通常是 'id'）
                try:
                    primary_keys = model._get_primary_keys_from_schema()
                    group_keys = [k for k in primary_keys if k != date_field]
                    stock_id_field = group_keys[0] if group_keys else 'id'  # 默认使用 'id'
                except Exception:
                    stock_id_field = 'id'  # 降级使用 'id'
                
                result = {}
                for record in latest_records:
                    stock_id = record.get(stock_id_field)
                    latest_date = record.get(date_field)
                    if stock_id and latest_date:
                        result[stock_id] = latest_date
                
                return result if result else None
            except (AttributeError, Exception) as e:
                # 如果 load_latest_records 不存在或失败，降级到简单查询
                logger.debug(f"使用 load_latest_records 失败: {e}，降级到简单查询")
                # 对于需要分组的情况，降级查询无法获取 per stock 信息，返回 None
                return None
        except Exception as e:
            logger.warning(f"查询数据库失败 {table_name}.{date_field}: {e}")
        
        return None
