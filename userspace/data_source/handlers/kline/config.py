"""
KlineHandler 配置

用户自定义的 KlineHandler 配置类。
"""
from dataclasses import dataclass
from typing import Optional

from core.modules.data_source.definition.handler_config import BaseHandlerConfig


@dataclass
class KlineHandlerConfig(BaseHandlerConfig):
    """
    KlineHandler 配置
    
    用于 K 线数据 Handler 的配置。
    """
    debug_limit_stocks: Optional[int] = None  # 调试模式：限制股票数量
