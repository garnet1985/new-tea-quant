"""
指数数据服务模块（IndexService）

职责：
- 封装指数指标相关的查询和数据操作
- 提供指数指标和指数成分股权重的访问接口

涉及的表：
- stock_index_indicator: 指数指标数据
- stock_index_indicator_weight: 指数成分股权重数据
"""

from .index_service import IndexService

__all__ = [
    'IndexService',
]
