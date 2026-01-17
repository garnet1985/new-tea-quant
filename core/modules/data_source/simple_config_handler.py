"""
SimpleConfigHandler - 纯配置驱动的 Handler

这是一个通用的 Handler，可以通过配置完成简单的数据获取任务，无需编写代码。

适用场景：
- 简单的 API 调用（单次调用，无复杂逻辑）
- 需要字段映射
- 可选：滚动刷新
- 可选：自动保存到数据库

配置示例（在 mapping.json 中）：
{
  "data_source_name": {
    "handler": "core.modules.data_source.simple_config_handler.SimpleConfigHandler",
    "handler_config": {
      "provider_name": "tushare",
      "method": "get_stock_list",
      "field_mapping": {
        "code": "ts_code",
        "name": "name"
      },
      "table_name": "stock_list",
      "date_field": "date",
      "requires_date_range": false
    }
  }
}

如果需要滚动刷新：
{
  "data_source_name": {
    "handler": "core.modules.data_source.simple_config_handler.SimpleConfigHandler",
    "handler_config": {
      "provider_name": "tushare",
      "method": "get_gdp",
      "date_format": "quarter",
      "rolling_unit": "quarter",
      "rolling_length": 4,
      "default_date_range": {"years": 5},
      "table_name": "gdp",
      "date_field": "quarter",
      "requires_date_range": true
    }
  }
}
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
from core.modules.data_source.data_classes import DataSourceTask


class SimpleConfigHandler(BaseDataSourceHandler):
    """
    纯配置驱动的 Handler
    
    通过配置完成数据获取，无需编写代码。
    适用于简单的数据源，只需要：
    - 调用一次 API
    - 字段映射
    - 可选：滚动刷新
    - 可选：自动保存
    
    注意：
    - data_source 名称会从 DataSourceDefinition 中自动获取
    - 如果配置了滚动刷新相关参数，会自动启用滚动刷新逻辑
    - 如果配置了 table_name，会自动保存数据到数据库
    """
    
    # 这些属性会在运行时动态设置
    data_source: str = None
    description: str = "SimpleConfigHandler - 纯配置驱动的 Handler"
    dependencies: List[str] = []
    requires_date_range: bool = False
    
    def __init__(self, schema, data_manager=None, definition=None):
        super().__init__(schema, data_manager, definition)
        
        # 从 definition 中获取 data_source 名称
        if definition and definition.data_source:
            self.data_source = definition.data_source
            self.description = f"SimpleConfigHandler for {self.data_source}"
        
        # 从配置的 API 中获取第一个 API 作为默认（用于简单场景）
        handler_config = self.get_handler_config()
        if handler_config and handler_config.apis:
            # 使用第一个 API 作为默认
            first_api_name = list(handler_config.apis.keys())[0]
            first_api_job = self.get_api_job(first_api_name)
            if first_api_job:
                self.provider_name = first_api_job.provider_name
                self.method = first_api_job.method
                # 从配置中获取 field_mapping（如果有）
                first_api_config = handler_config.apis[first_api_name]
                self.field_mapping = first_api_config.get("field_mapping", {}) or {}
            else:
                raise ValueError(f"无法获取 API '{first_api_name}' 的配置")
        else:
            raise ValueError(f"{self.data_source} Handler 必须配置至少一个 API（在 handler_config.apis 中）")
        
        # 检查是否需要滚动刷新（根据 renew_mode 判断）
        renew_mode = self.get_param("renew_mode")
        if renew_mode == "rolling":
            # 启用滚动刷新
            self.date_format = self.get_param("date_format", "date")
            self.default_date_range = self.get_param("default_date_range", {"years": 5})
            self.table_name = self.get_param("table_name", None)
            self.date_field = self.get_param("date_field", None)
            self.requires_date_range = self.get_param("requires_date_range", True)
            self._enable_rolling = True
            
            # 如果未配置 table_name，使用 data_source 名称
            if self.table_name is None:
                self.table_name = self.data_source
            
            # 如果未配置 date_field，根据 date_format 自动识别
            if self.date_field is None:
                self.date_field = self._get_default_date_field_for_format(self.date_format)
        else:
            # 不使用滚动刷新
            self.requires_date_range = self.get_param("requires_date_range", False)
            self.table_name = self.get_param("table_name", None)
            self.date_field = self.get_param("date_field", None)
            self._enable_rolling = False
            
            # 如果未配置 date_field，使用默认值
            if self.date_field is None:
                self.date_field = "date"
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段 - 如果启用了滚动刷新，计算日期范围
        
        使用 RollingRenewService 处理逻辑。
        """
        if context is None:
            context = {}
        
        # 如果启用了滚动刷新，使用 service 计算日期范围
        if self._enable_rolling:
            from core.modules.data_source.services import RollingRenewService
            
            # 获取滚动刷新配置
            rolling_unit = self.get_param("rolling_unit")
            rolling_length = self.get_param("rolling_length")
            
            if rolling_unit is None or rolling_length is None:
                logger.warning(
                    f"Rolling mode 需要 rolling_unit 和 rolling_length，跳过自动处理 "
                    f"(handler: {self.data_source}, rolling_unit: {rolling_unit}, rolling_length: {rolling_length})"
                )
                return context
            
            # 使用 service 计算日期范围
            service = RollingRenewService(data_manager=self.data_manager)
            start_date, end_date = service.calculate_date_range(
                date_format=self.date_format,
                rolling_unit=rolling_unit,
                rolling_length=rolling_length,
                table_name=self.table_name,
                date_field=self.date_field,
                context=context
            )
            
            context["start_date"] = start_date
            context["end_date"] = end_date
        
        return context
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """生成获取数据的 Task"""
        context = context or {}
        
        # 构建 API 参数
        api_params = {}
        
        # 如果需要日期范围，从 context 获取
        if self.requires_date_range:
            start_date = context.get("start_date")
            end_date = context.get("end_date")
            
            if start_date and end_date:
                api_params["start_date"] = start_date
                api_params["end_date"] = end_date
        
        # 合并其他参数
        extra_params = self.get_param("extra_params", {})
        api_params.update(extra_params)
        context_params = context.get("extra_params", {})
        api_params.update(context_params)
        
        # 从缓存的 API Job 创建 Task
        handler_config = self.get_handler_config()
        if handler_config and handler_config.apis:
            first_api_name = list(handler_config.apis.keys())[0]
            api_job = self.get_api_job_with_params(
                name=first_api_name,
                params=api_params
            )
            task = DataSourceTask(
                task_id=f"{self.data_source}_task",
                api_jobs=[api_job],
                description=f"获取 {self.data_source} 数据"
            )
            return [task]
        else:
            raise ValueError(f"{self.data_source} Handler 必须配置至少一个 API")
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """标准化数据 - 使用字段映射"""
        # 使用默认逻辑：单 API 场景
        df = self.get_simple_result(task_results)
        
        if df is None or df.empty:
            logger.warning(f"{self.data_source} 数据查询返回空数据")
            return {"data": []}
        
        # 转换为字典列表并应用字段映射（使用辅助方法）
        records = df.to_dict('records')
        formatted = self._apply_field_mapping(records, self.field_mapping)
        
        logger.info(f"✅ {self.data_source} 数据处理完成，共 {len(formatted)} 条记录")
        
        return {"data": formatted}
    
    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """标准化后处理 - 如果配置了 table_name，自动保存数据"""
        context = context or {}
        
        # 如果配置了 table_name，自动保存数据
        if self.table_name:
            self._save_normalized_data(
                normalized_data=normalized_data,
                context=context,
                table_name=self.table_name,
                date_field=self.date_field
            )
