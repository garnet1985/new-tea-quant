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
    - rolling_periods: 4
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
        context = context or {}
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过 GDP 数据保存")
            return
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存 GDP 数据")
            return
        
        # 验证数据格式
        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug("GDP 数据为空，无需保存")
            return
        
        try:
            # 清理 NaN 值
            from core.infra.db.helpers.db_helpers import DBHelper
            data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)
            
            # 使用 service 保存数据
            count = self.data_manager.macro.save_gdp_data(data_list)
            logger.info(f"✅ GDP 数据保存完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存 GDP 数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
