"""
Shibor Handler - Shibor 数据 Handler

Shibor（上海银行间同业拆放利率）数据获取 Handler，支持日期数据的滚动刷新机制。

注意：这是一个简单的 Handler，只需要实现 on_after_normalize 保存数据，其他都由基类自动处理。
"""
from typing import Dict, Any
from loguru import logger
import pandas as pd

from core.modules.data_source.base_class.base_handler import BaseHandler


class ShiborHandler(BaseHandler):
    """
    Shibor Handler
    
    Shibor 数据获取 Handler，使用日期数据格式，默认滚动刷新最近 30 天。
    
    配置（在 config.json 中）：
    - renew_mode: "rolling"
    - date_format: "day"
    - rolling_unit: "day", rolling_length: 30
    - apis: {...} (包含 provider_name, method, field_mapping 等)
    """
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：数据清洗（NaN 清理），不负责保存。
        
        注意：data source 不负责 save，save 由上层（data_manager/service）自己处理。
        """
        # 可选：清洗 NaN 值
        return self.clean_nan_in_normalized_data(normalized_data, default=None)
