"""
Renew Manager

负责根据 renew_mode 和表状态决定日期范围，并将日期范围注入到 ApiJob 的 params 中。

设计目标：
- 作为 renew 工作的统一编排层
- 集中管理所有 renew 相关的判断逻辑和业务逻辑
- 支持查表操作（判断表是否为空、查询最新日期等）
- 根据 renew_mode 路由到对应的具体 Service 计算日期范围
- 返回已注入日期范围的 ApiJob 列表
"""
from typing import Any, Dict, List, Tuple, Optional, Union
from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper


class RenewManager:
    """
    Renew Manager - 统一编排层，管理日期范围决策逻辑
    
    职责（编排层）：
    1. 判断是否已显式指定日期范围
    2. 判断表是否为空（需要 data_manager）
    3. 根据 renew_mode 决定日期范围策略
    4. 路由到对应的具体 Service（IncrementalRenewService, RollingRenewService, RefreshRenewService）计算精确日期范围
    5. 将日期范围注入到 ApiJob 的 params 中
    
    注意：使用 RenewCommonHelper 提供公共方法，底层实现由不同 mode 的 service 提供
    """
    
    def __init__(self, data_manager=None):
        """
        初始化 Renew Manager
        
        Args:
            data_manager: DataManager 实例（用于查询数据库，判断表是否为空等）
        """
        self.data_manager = data_manager
    
    # ========== 判断方法 ==========
    
    def is_date_range_specified(self, context: Dict[str, Any]) -> bool:
        """判断 context 中是否已经显式指定了 start_date / end_date"""
        if not context:
            return False
        return "start_date" in context and "end_date" in context
    
    def get_renew_mode(self, context: Dict[str, Any]) -> str:
        """从 context.config 中读取 renew_mode（小写字符串）"""
        config = self._get_config(context)
        return config.get_renew_mode()
    
    def has_rolling_time_range(self, context: Dict[str, Any]) -> bool:
        """是否配置了滚动时间窗口（rolling_unit + rolling_length）"""
        config = self._get_config(context)
        return bool(config.get_rolling_unit() and config.get_rolling_length())
    
    def is_table_empty(self, context: Dict[str, Any]) -> bool:
        """
        判断目标表是否为空。
        
        优先级：
        1. 如果 context 中有 is_table_empty 标记，直接使用
        2. 如果有 data_manager 和 table_name，查询数据库
        3. 否则返回 False（假设表不为空）
        """
        # 优先使用 context 中的标记
        if "is_table_empty" in context:
            return bool(context.get("is_table_empty"))
        
        # 如果没有标记，尝试查询数据库
        if not self.data_manager:
            return False
        
        config = self._get_config(context)
        table_name = config.get_table_name()
        
        if not table_name:
            # 没有表名，无法查询，假设表不为空
            return False
        
        try:
            # 查询表是否有数据
            model = self.data_manager.get_table(table_name)
            if model:
                # 尝试加载一条记录
                latest_record = model.load_latest()
                is_empty = latest_record is None
                logger.debug(f"查询表 {table_name} 状态: {'空' if is_empty else '非空'}")
                return is_empty
        except Exception as e:
            logger.warning(f"查询表 {table_name} 是否为空时出错: {e}，假设表不为空")
        
        return False
    
    # ========== 日期范围计算方法 ==========
    
    def compute_default_date_range(self, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        计算默认日期范围（不依赖数据库）。
        
        使用 config.default_date_range 配置，如果没有则使用系统默认值。
        """
        config = self._get_config(context)
        date_format = config.get_date_format()
        default_range = config.get_default_date_range()
        
        # 直接调用 RefreshRenewService 计算默认日期范围
        try:
            from core.modules.data_source.service.renew.refresh_renew_service import RefreshRenewService
            service = RefreshRenewService(data_manager=self.data_manager)
            start, end = service.calculate_date_range(
                date_format=date_format,
                default_date_range=default_range,
                context=context
            )
            return start, end
        except Exception as e:
            logger.warning(f"使用 RefreshRenewService 计算默认日期范围失败: {e}，使用系统默认日期范围")
            # 降级到系统默认日期范围（使用 helper 方法）
            return RenewCommonHelper.get_default_date_range(self.data_manager, date_format, context)
    
    def compute_incremental_date_range(self, context: Dict[str, Any]) -> Union[Tuple[str, str], Dict[str, Tuple[str, str]]]:
        """
        计算增量模式下的日期范围（需要查表）。
        
        调用 IncrementalRenewService 计算精确的增量日期范围。
        
        Returns:
            - 如果需要按股票分组：Dict[str, Tuple[str, str]] {stock_id: (start_date, end_date)}
            - 如果不需要分组：Tuple[str, str] (start_date, end_date)
        """
        config = self._get_config(context)
        date_format = config.get_date_format()
        table_name = config.get_table_name()
        date_field = config.get_date_field()

        # 配置验证已在 DataSourceManager._discover_config 阶段完成，这里直接使用
        
        try:
            from core.modules.data_source.service.renew.incremental_renew_service import IncrementalRenewService
            service = IncrementalRenewService(data_manager=self.data_manager)
            result = service.calculate_date_range(
                date_format=date_format,
                table_name=table_name,
                date_field=date_field,
                context=context
            )
            return result
        except Exception as e:
            logger.warning(f"使用 IncrementalRenewService 计算增量日期范围失败: {e}，使用默认日期范围")
            return self.compute_default_date_range(context)
    
    def compute_rolling_date_range(self, context: Dict[str, Any]) -> Union[Tuple[str, str], Dict[str, Tuple[str, str]]]:
        """
        计算滚动模式下的日期范围（需要查表）。
        
        调用 RollingRenewService 计算精确的滚动日期范围。
        
        Returns:
            - 如果需要按股票分组：Dict[str, Tuple[str, str]] {stock_id: (start_date, end_date)}
            - 如果不需要分组：Tuple[str, str] (start_date, end_date)
        """
        config = self._get_config(context)
        date_format = config.get_date_format()
        rolling_unit = config.get_rolling_unit()
        rolling_length = config.get_rolling_length()
        table_name = config.get_table_name()
        date_field = config.get_date_field()

        # 配置验证已在 DataSourceManager._discover_config 阶段完成，这里直接使用
        
        try:
            from core.modules.data_source.service.renew.rolling_renew_service import RollingRenewService
            service = RollingRenewService(data_manager=self.data_manager)
            result = service.calculate_date_range(
                date_format=date_format,
                rolling_unit=rolling_unit,
                rolling_length=rolling_length,
                table_name=table_name,
                date_field=date_field,
                context=context
            )
            return result
        except Exception as e:
            logger.warning(f"使用 RollingRenewService 计算滚动日期范围失败: {e}，使用默认日期范围")
            return self.compute_default_date_range(context)
    
    # ========== 辅助方法 ==========
    
    def _get_config(self, context: Dict[str, Any]):
        """
        从 context 中获取 config，必须为 DataSourceConfig 实例。
        不接受 dict，进入主程序前必须已完成转换。
        """
        from core.modules.data_source.data_class.config import DataSourceConfig
        from core.modules.data_source.data_class.error import DataSourceConfigError

        config = context.get("config")
        if config is None:
            raise DataSourceConfigError("context 中缺少 config")
        if not isinstance(config, DataSourceConfig):
            raise DataSourceConfigError(
                f"config 必须是 DataSourceConfig 实例，收到: {type(config).__name__}"
            )
        return config
    
    def add_date_range(
        self,
        apis: List[ApiJob],
        start_date: Any,
        end_date: Any,
        per_stock_date_ranges: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> List[ApiJob]:
        """
        将 start_date / end_date 注入到每个 ApiJob 的 params 中。
        
        委托给 DataSourceHandlerHelper.add_date_range 实现。
        """
        from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
        return DataSourceHandlerHelper.add_date_range(
            apis, start_date, end_date, per_stock_date_ranges
        )
