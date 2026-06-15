"""
Utils Package - 通用工具模块

提供各种与业务无关的辅助工具：
- date: 日期工具
- math: 数值 / 确定性随机
- icon: 图标服务
- utils: 类型判断与 DataFrame 薄封装（Utils 类）
"""
from .icon.icon_service import IconService, i as icon_i
try:
    from .utils import Utils
except ModuleNotFoundError as exc:
    # Allow lightweight imports (e.g. setup scripts only needing icon `i`)
    # before optional heavy dependencies such as pandas are installed.
    if exc.name != "pandas":
        raise
    Utils = None  # type: ignore[assignment]

try:
    from .date.date_utils import DateUtils
except ModuleNotFoundError as exc:
    if exc.name != "pandas":
        raise
    DateUtils = None  # type: ignore[assignment]

from .math import deterministic_unit_float

__all__ = [
    'Utils',
    'deterministic_unit_float',
    'DateUtils',
    'IconService',
    'i',
]

# 导出简化的图标函数（别名）
i = icon_i
