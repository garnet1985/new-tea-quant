"""跨回测层枚举结果 contract（对象 + 管理器）。

机会盘点落盘、价格回测 worker、组合 build_events、机会盘点报告 / 分析 / BFF 已接入。
"""

from .enum_result import CompletedGoal, EnumResult
from .enum_results_manager import EnumResultsManager

__all__ = [
    "CompletedGoal",
    "EnumResult",
    "EnumResultsManager",
]
