"""
KlineHandler 配置

用户自定义的 KlineHandler 配置类。
"""
from dataclasses import dataclass
from typing import Optional

from core.modules.data_source.data_classes.handler_config import IncrementalConfig


@dataclass
class KlineHandlerConfig(IncrementalConfig):
    """
    KlineHandler 配置
    
    用于 K 线数据 Handler 的配置。
    
    继承 IncrementalConfig，因为 KlineHandler 使用 incremental 模式。
    """
    debug_limit_stocks: Optional[int] = None  # 调试模式：限制股票数量
