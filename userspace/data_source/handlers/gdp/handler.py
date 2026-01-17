"""
GDP Handler - GDP 数据 Handler

GDP（国内生产总值）数据获取 Handler，支持季度数据的滚动刷新机制。

注意：这是一个简单的 Handler，只需要定义 data_source，其他都由基类自动处理。
"""
from typing import Dict, Any
from loguru import logger

from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler


class GdpHandler(BaseDataSourceHandler):
    """
    GDP Handler
    
    GDP 数据获取 Handler，使用季度数据格式，默认滚动刷新最近 4 个季度。
    
    配置（在 mapping.json 或 config.json 中）：
    - provider_name: "tushare"
    - method: "get_gdp"
    - date_format: "quarter"
    - rolling_unit: "quarter", rolling_length: 4
    - field_mapping: {...}
    """
    
    data_source = "gdp"
    description = "GDP 数据 Handler（季度数据，滚动刷新）"
    dependencies = []
    requires_date_range = True
    
    # 注意：不需要实现 __init__, fetch, normalize
    # - __init__: 基类自动初始化配置（依赖注入）
    # - fetch: 基类自动创建 Task（如果配置了 provider_name 和 method）
    # - normalize: 基类自动应用字段映射（如果配置了 field_mapping）
    
    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """
        标准化后处理：保存数据到数据库
        """
        self._save_data_with_clean_nan(
            normalized_data=normalized_data,
            context=context,
            save_method=self.data_manager.macro.save_gdp_data,
            data_source_name="GDP"
        )
