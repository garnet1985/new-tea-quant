"""跨回测层枚举结果 contract（对象 + 管理器；尚未接入各引擎）。"""

from .enum_result import CompletedGoal, EnumResult
from .enum_results_manager import EnumResultsManager

__all__ = [
    "CompletedGoal",
    "EnumResult",
    "EnumResultsManager",
]
