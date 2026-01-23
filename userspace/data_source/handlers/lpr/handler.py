"""
LPR Handler - LPR 数据 Handler

LPR（贷款市场报价利率）数据获取 Handler，支持日期数据的滚动刷新机制。

注意：这是一个简单的 Handler，只需要实现 on_after_normalize 保存数据，其他都由基类自动处理。
"""
from typing import Dict, Any
from loguru import logger
import pandas as pd

from core.modules.data_source.base_class.base_handler import BaseHandler


class LprHandler(BaseHandler):
    """
    LPR Handler
    
    LPR 数据获取 Handler，使用日期数据格式，默认滚动刷新最近 30 天。
    
    配置（在 config.json 中）：
    - renew_mode: "rolling"
    - date_format: "day"
    - rolling_unit: "day", rolling_length: 30
    - apis: {...} (包含 provider_name, method, field_mapping 等)
    """
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：数据清洗（NaN 清理）已在基类中自动处理，这里直接返回。
        
        注意：data source 不负责 save，save 由上层（data_manager/service）自己处理。
        """
        # 基类已自动清洗 NaN（date_format="day" 会使用 default=0.0），直接返回
        return normalized_data
