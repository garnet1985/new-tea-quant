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
        标准化后处理：数据清洗（NaN 清理）已在基类中自动处理，这里直接返回。
        
        注意：data source 不负责 save，save 由上层（data_manager/service）自己处理。
        """
        # 基类已自动清洗 NaN（date_format="quarter" 会使用 default=None），直接返回
        return normalized_data
