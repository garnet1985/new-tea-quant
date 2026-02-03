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
    pass

