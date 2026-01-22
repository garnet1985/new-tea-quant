"""
GDP Handler - GDP 数据 Handler

GDP（国内生产总值）数据获取 Handler，支持季度数据的滚动刷新机制。

注意：这是一个简单的 Handler，只需要实现 on_after_normalize 保存数据，其他都由基类自动处理。
"""
from typing import Dict, Any
from loguru import logger
import pandas as pd

from core.modules.data_source.base_class.base_handler import BaseHandler


class GdpHandler(BaseHandler):
    """
    GDP Handler
    
    GDP 数据获取 Handler，使用季度数据格式，默认滚动刷新最近 4 个季度。
    
    配置（在 config.json 中）：
    - renew_mode: "rolling"
    - date_format: "quarter"
    - rolling_unit: "quarter", rolling_length: 4
    - apis: {...} (包含 provider_name, method, field_mapping 等)
    """
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：保存数据到数据库
        
        Args:
            context: 执行上下文
            normalized_data: 标准化后的数据
            
        Returns:
            Dict[str, Any]: 返回标准化后的数据
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法保存 GDP 数据")
            return normalized_data
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过 GDP 数据保存")
            return normalized_data
        
        # 提取数据列表
        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug("GDP 数据为空，无需保存")
            return normalized_data
        
        try:
            # 清理 NaN 值
            df = pd.DataFrame(data_list)
            df = df.replace({pd.NA: None, float('nan'): None})
            cleaned_data = df.to_dict('records')
            
            # 保存数据
            count = data_manager.macro.save_gdp_data(cleaned_data)
            logger.info(f"✅ 保存 GDP 数据完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存 GDP 数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        return normalized_data
