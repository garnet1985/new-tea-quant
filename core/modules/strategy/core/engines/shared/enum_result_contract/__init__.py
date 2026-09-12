"""跨回测层枚举结果 contract（对象 + 管理器）。

枚举落盘与价格回测 worker 已接入；组合仍读 CSV。
"""

from .enum_result import CompletedGoal, EnumResult
from .enum_results_manager import EnumResultsManager

__all__ = [
    "CompletedGoal",
    "EnumResult",
    "EnumResultsManager",
]
