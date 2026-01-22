"""
Renew Mode Service

统一入口，根据 renew_mode 路由到对应的 Service。
"""
from typing import Dict, Any, Tuple, Optional, Union
from loguru import logger

from core.global_enums.enums import UpdateMode, TimeUnit
from .incremental_renew_service import IncrementalRenewService
from .rolling_renew_service import RollingRenewService
from .refresh_renew_service import RefreshRenewService


class RenewModeService:
    """
    Renew Mode Service - 统一入口
    
    根据 renew_mode 路由到对应的 Service，简化 Handler 的调用。
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
        renew_mode: str,
        date_format: str,
        context: Dict[str, Any] = None,
        # Incremental 模式参数
        table_name: Optional[str] = None,
        date_field: Optional[str] = None,
        # Rolling 模式参数
        rolling_unit: Optional[str] = None,
        rolling_length: Optional[int] = None,
        # Refresh 模式参数
        default_date_range: Optional[Dict[str, int]] = None
    ) -> Union[Tuple[str, str], Dict[str, Tuple[str, str]]]:
        """
        根据 renew_mode 计算日期范围（统一入口）
        
        Args:
            renew_mode: 更新模式（"incremental" | "rolling" | "refresh"）
            date_format: 日期格式（"quarter" | "month" | "day"）
            context: 执行上下文
            table_name: 数据库表名（incremental/rolling 模式需要）
            date_field: 日期字段名（incremental/rolling 模式需要）
            rolling_unit: 滚动单位（rolling 模式需要）
            rolling_length: 滚动长度（rolling 模式需要）
            default_date_range: 默认日期范围（refresh 模式需要）
        
        Returns:
            - 如果需要按股票分组：Dict[str, Tuple[str, str]] {stock_id: (start_date, end_date)}
            - 如果不需要分组：Tuple[str, str] (start_date, end_date)
        
        Raises:
            ValueError: 如果 renew_mode 无效或缺少必需参数
        """
        context = context or {}
        
        # 支持枚举和字符串两种格式（兼容性）
        if isinstance(renew_mode, UpdateMode):
            renew_mode = renew_mode.value
        if isinstance(date_format, TimeUnit):
            date_format = date_format.value
        if isinstance(rolling_unit, TimeUnit):
            rolling_unit = rolling_unit.value
        
        if renew_mode == UpdateMode.INCREMENTAL.value:
            if not table_name or not date_field:
                raise ValueError(
                    f"Incremental mode 需要 table_name 和 date_field 参数"
                )
            service = IncrementalRenewService(data_manager=self.data_manager)
            return service.calculate_date_range(
                date_format=date_format,
                table_name=table_name,
                date_field=date_field,
                context=context
            )
        
        elif renew_mode == UpdateMode.ROLLING.value:
            if not table_name or not date_field:
                raise ValueError(
                    f"Rolling mode 需要 table_name 和 date_field 参数"
                )
            if not rolling_unit or not rolling_length:
                raise ValueError(
                    f"Rolling mode 需要 rolling_unit 和 rolling_length 参数"
                )
            service = RollingRenewService(data_manager=self.data_manager)
            return service.calculate_date_range(
                date_format=date_format,
                rolling_unit=rolling_unit,
                rolling_length=rolling_length,
                table_name=table_name,
                date_field=date_field,
                context=context
            )
        
        elif renew_mode == UpdateMode.REFRESH.value:
            service = RefreshRenewService(data_manager=self.data_manager)
            return service.calculate_date_range(
                date_format=date_format,
                default_date_range=default_date_range or {},
                context=context
            )
        
        else:
            valid_modes = [UpdateMode.INCREMENTAL.value, UpdateMode.ROLLING.value, UpdateMode.REFRESH.value]
            raise ValueError(
                f"未知的 renew_mode: {renew_mode}，支持的模式: {', '.join(valid_modes)}"
            )
