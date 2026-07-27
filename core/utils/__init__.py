"""
Utils Package - 通用工具模块

提供各种与业务无关的辅助工具：
- date: 日期工具
- math: 数值 / 确定性随机
- utils: 类型判断与 DataFrame 薄封装（Utils 类）

CLI 图标请使用 ``core.infra.cmd_layout.CmdLayout.icon``。
"""
try:
    from .utils import Utils
except ModuleNotFoundError as exc:
    # Allow lightweight imports before optional heavy dependencies such as pandas.
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
    "Utils",
    "deterministic_unit_float",
    "DateUtils",
]
