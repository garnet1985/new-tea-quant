"""报告用数字格式：固定小数位，可读优先（非精确计算输出）。"""

from __future__ import annotations

from typing import Any

# 相关 / R² / 滞后相关
DIGITS_CORR = 2
# β / α / 倍数
DIGITS_COEF = 2
# 百分比（翻转率等）
DIGITS_PCT = 0


def fmt_num(value: Any, digits: int = DIGITS_CORR) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{int(digits)}f}"
    except (TypeError, ValueError):
        return str(value)


def fmt_corr(value: Any) -> str:
    return fmt_num(value, DIGITS_CORR)


def fmt_coef(value: Any) -> str:
    return fmt_num(value, DIGITS_COEF)


def fmt_pct(value: Any) -> str:
    """``value`` 为 0~1 比例 → ``2%``。"""
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.{DIGITS_PCT}f}%"
    except (TypeError, ValueError):
        return str(value)


__all__ = [
    "DIGITS_CORR",
    "DIGITS_COEF",
    "DIGITS_PCT",
    "fmt_num",
    "fmt_corr",
    "fmt_coef",
    "fmt_pct",
]
