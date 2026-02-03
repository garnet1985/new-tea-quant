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