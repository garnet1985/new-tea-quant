"""
Renew Service

负责根据 renew_mode 和表状态决定日期范围，并将日期范围注入到 ApiJob 的 params 中。

设计目标：
- 集中管理所有 renew 相关的判断逻辑和业务逻辑
- 支持查表操作（判断表是否为空、查询最新日期等）
- 委托给 legacy 的 RenewModeService 执行实际的日期范围计算
- 返回已注入日期范围的 ApiJob 列表
"""
from typing import Any, Dict, List, Tuple, Optional
from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob
from core.global_enums.enums import UpdateMode


class RenewService:
    """
    Renew Service - 统一管理日期范围决策逻辑
    
    职责：
    1. 判断是否已显式指定日期范围
    2. 判断表是否为空（需要 data_manager）
    3. 根据 renew_mode 决定日期范围策略
    4. 调用 legacy RenewModeService 计算精确日期范围
    5. 将日期范围注入到 ApiJob 的 params 中
    """
    
    def __init__(self, data_manager=None):
        """
        初始化 Renew Service
        
        Args:
            data_manager: DataManager 实例（用于查询数据库，判断表是否为空等）
        """
        self.data_manager = data_manager
        # 延迟导入 legacy RenewModeService，避免循环依赖
        self._renew_mode_service = None
    
    def _get_renew_mode_service(self):
        """延迟初始化 RenewModeService"""
        if self._renew_mode_service is None:
            from core.modules.data_source.services.renew_mode_service import RenewModeService
            self._renew_mode_service = RenewModeService(data_manager=self.data_manager)
        return self._renew_mode_service
    
    # ========== 判断方法 ==========
    
    def is_date_range_specified(self, context: Dict[str, Any]) -> bool:
        """判断 context 中是否已经显式指定了 start_date / end_date"""
        if not context:
            return False
        return "start_date" in context and "end_date" in context
    
    def get_renew_mode(self, context: Dict[str, Any]) -> str:
        """从 context.config 中读取 renew_mode（小写字符串）"""
        config = self._get_config_dict(context)
        mode = (config.get("renew_mode") or "").lower()
        return mode
    
    def has_rolling_time_range(self, context: Dict[str, Any]) -> bool:
        """是否配置了滚动时间窗口（rolling_unit + rolling_length）"""
        config = self._get_config_dict(context)
        return bool(config.get("rolling_unit") and config.get("rolling_length"))
    
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
        
        config = self._get_config_dict(context)
        table_name = config.get("table_name")
        
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
        config = self._get_config_dict(context)
        date_format = (config.get("date_format") or "day").lower()
        default_range = config.get("default_date_range") or {}
        
        # 调用 legacy RefreshRenewService 计算默认日期范围
        renew_mode_service = self._get_renew_mode_service()
        try:
            start, end = renew_mode_service.calculate_date_range(
                renew_mode=UpdateMode.REFRESH.value,
                date_format=date_format,
                context=context,
                default_date_range=default_range
            )
            return start, end
        except Exception as e:
            logger.warning(f"使用 RenewModeService 计算默认日期范围失败: {e}，使用简化计算")
            # 降级到简化计算
            return self._compute_simple_default_date_range(config)
    
    def compute_incremental_date_range(self, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        计算增量模式下的日期范围（需要查表）。
        
        调用 legacy IncrementalRenewService 计算精确的增量日期范围。
        """
        config = self._get_config_dict(context)
        date_format = (config.get("date_format") or "day").lower()
        table_name = config.get("table_name")
        date_field = config.get("date_field")
        
        if not table_name or not date_field:
            logger.warning(
                f"增量模式需要 table_name 和 date_field，当前配置: "
                f"table_name={table_name}, date_field={date_field}，使用默认日期范围"
            )
            return self.compute_default_date_range(context)
        
        renew_mode_service = self._get_renew_mode_service()
        try:
            start, end = renew_mode_service.calculate_date_range(
                renew_mode=UpdateMode.INCREMENTAL.value,
                date_format=date_format,
                context=context,
                table_name=table_name,
                date_field=date_field
            )
            return start, end
        except Exception as e:
            logger.warning(f"使用 RenewModeService 计算增量日期范围失败: {e}，使用默认日期范围")
            return self.compute_default_date_range(context)
    
    def compute_rolling_date_range(self, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        计算滚动模式下的日期范围（需要查表）。
        
        调用 legacy RollingRenewService 计算精确的滚动日期范围。
        """
        config = self._get_config_dict(context)
        date_format = (config.get("date_format") or "day").lower()
        rolling_unit = config.get("rolling_unit")
        rolling_length = config.get("rolling_length")
        table_name = config.get("table_name")
        date_field = config.get("date_field")
        
        if not table_name or not date_field:
            logger.warning(
                f"滚动模式需要 table_name 和 date_field，当前配置: "
                f"table_name={table_name}, date_field={date_field}，使用默认日期范围"
            )
            return self.compute_default_date_range(context)
        
        if not rolling_unit or not rolling_length:
            logger.warning(
                f"滚动模式需要 rolling_unit 和 rolling_length，当前配置: "
                f"rolling_unit={rolling_unit}, rolling_length={rolling_length}，使用默认日期范围"
            )
            return self.compute_default_date_range(context)
        
        renew_mode_service = self._get_renew_mode_service()
        try:
            start, end = renew_mode_service.calculate_date_range(
                renew_mode=UpdateMode.ROLLING.value,
                date_format=date_format,
                context=context,
                table_name=table_name,
                date_field=date_field,
                rolling_unit=rolling_unit,
                rolling_length=rolling_length
            )
            return start, end
        except Exception as e:
            logger.warning(f"使用 RenewModeService 计算滚动日期范围失败: {e}，使用默认日期范围")
            return self.compute_default_date_range(context)
    
    def _compute_simple_default_date_range(self, config: Dict[str, Any]) -> Tuple[str, str]:
        """
        简化的默认日期范围计算（降级方案，不依赖 RenewModeService）。
        
        仅用于 RenewModeService 调用失败时的降级方案。
        """
        date_format = (config.get("date_format") or "day").lower()
        default_range = config.get("default_date_range") or {}
        years = int(default_range.get("years") or 1)
        
        from datetime import datetime, timedelta
        
        today = datetime.today()
        if date_format in ("day", "date"):
            end = today
            start = today - timedelta(days=365 * years)
            fmt = "%Y-%m-%d"
            return start.strftime(fmt), end.strftime(fmt)
        elif date_format == "month":
            end = today
            start = today - timedelta(days=30 * 12 * years)
            return start.strftime("%Y-%m"), end.strftime("%Y-%m")
        elif date_format == "quarter":
            year = today.year
            quarter = (today.month - 1) // 3 + 1
            end_str = f"{year}Q{quarter}"
            start_year = year - years
            start_str = f"{start_year}Q1"
            return start_str, end_str
        else:
            # 未知格式，返回当前日期
            return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    
    # ========== 辅助方法 ==========
    
    def _get_config_dict(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        从 context 中获取 config，支持对象和字典两种格式。
        
        如果 config 是对象（如 DataSourceConfig），转换为字典；
        如果已经是字典，直接返回。
        """
        config = context.get("config")
        if config is None:
            return {}
        
        # 如果是字典，直接返回
        if isinstance(config, dict):
            return config
        
        # 如果是对象，尝试转换为字典
        if hasattr(config, "__dict__"):
            return config.__dict__
        
        # 如果是 dataclass，使用 asdict
        try:
            from dataclasses import asdict
            if hasattr(config, "__dataclass_fields__"):
                return asdict(config)
        except Exception:
            pass
        
        # 降级：尝试通过 getattr 访问常见字段
        result = {}
        for attr in ["renew_mode", "date_format", "table_name", "date_field", 
                     "default_date_range", "rolling_unit", "rolling_length"]:
            if hasattr(config, attr):
                result[attr] = getattr(config, attr, None)
        
        return result
    
    def add_date_range(
        self,
        apis: List[ApiJob],
        start_date: Any,
        end_date: Any,
    ) -> List[ApiJob]:
        """
        将统一的 start_date / end_date 注入到每个 ApiJob 的 params 中。
        """
        for job in apis or []:
            params = job.params or {}
            if start_date is not None:
                params.setdefault("start_date", start_date)
            if end_date is not None:
                params.setdefault("end_date", end_date)
            job.params = params
        return apis
