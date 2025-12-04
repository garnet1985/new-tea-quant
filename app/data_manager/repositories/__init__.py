"""
Data Service 子模块

说明：
- 用于封装跨表 / 领域级的数据访问逻辑
- 由 DataManager 统一创建和管理

当前阶段：
- 仅提供占位模块，后续按领域 / 策略逐步补充具体 DataService 实现

示例命名约定（建议）：
- StockDataService    - 股票基础域（列表、K线、因子等）
- MacroDataService    - 宏观经济域（GDP、CPI、Shibor 等）
- WalyDataService     - Waly 策略相关数据（策略表 + 基础表联动）
"""

from typing import Dict, Any


class BaseDataService:
    """
    DataService 基类
    - 目前只是一个占位类，后续可以在这里放通用工具
    """

    def __init__(self, context: Dict[str, Any] | None = None):
        self.context = context or {}


__all__ = [
    "BaseDataService",
]


