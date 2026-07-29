"""Infra Utils — 与业务无关的通用工具。

- date: DateUtils
- math: deterministic_unit_float
- utils: Utils（类型判断与 DataFrame 薄封装）
- io: csv_io / file_io

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
