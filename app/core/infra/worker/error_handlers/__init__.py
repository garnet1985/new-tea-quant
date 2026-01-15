"""
错误处理器模块

提供多种错误处理策略：
- SimpleErrorHandler: 简单错误处理器
"""

from .base import ErrorHandler, ErrorAction
from .simple_error_handler import SimpleErrorHandler

__all__ = [
    'ErrorHandler',
    'ErrorAction',
    'SimpleErrorHandler',
]
