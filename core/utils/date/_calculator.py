"""
日期计算模块（内部使用）

职责：日期的加减、比较、边界计算，只处理日期（YYYYMMDD），不涉及周期。
"""
from datetime import datetime, timedelta
from typing import Optional

from core.utils.date._constants import FMT_YYYYMMDD
from core.utils.date._parser import normalize_date_str


def parse_date(date_str: str) -> datetime:
    """解析 YYYYMMDD 字符串为 datetime"""
    normalized = normalize_date_str(date_str)
    if not normalized:
        raise ValueError(f"日期格式错误: {date_str}，应为 YYYYMMDD")
    return datetime.strptime(normalized, FMT_YYYYMMDD)


def today_impl() -> str:
    """获取今天，返回 YYYYMMDD"""
    return datetime.now().strftime(FMT_YYYYMMDD)


def add_days_impl(date: str, days: int) -> str:
    """加 N 天"""
    dt = parse_date(date)
    result = dt + timedelta(days=days)
    return result.strftime(FMT_YYYYMMDD)


def sub_days_impl(date: str, days: int) -> str:
    """减 N 天"""
    return add_days_impl(date, -days)


def diff_days_impl(date1: str, date2: str) -> int:
    """计算天数差（date2 - date1）"""
    dt1 = parse_date(date1)
    dt2 = parse_date(date2)
    return (dt2 - dt1).days


def get_month_start_impl(date: str) -> str:
    """获取月初"""
    dt = parse_date(date)
    return dt.replace(day=1).strftime(FMT_YYYYMMDD)


def get_month_end_impl(date: str) -> str:
    """获取月末"""
    dt = parse_date(date)
    # 下个月第一天 - 1天
    if dt.month == 12:
        next_month = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        next_month = dt.replace(month=dt.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    return last_day.strftime(FMT_YYYYMMDD)


def get_quarter_start_impl(date: str) -> str:
    """获取季度初"""
    dt = parse_date(date)
    quarter = (dt.month - 1) // 3 + 1
    start_month = {1: 1, 2: 4, 3: 7, 4: 10}[quarter]
    return dt.replace(month=start_month, day=1).strftime(FMT_YYYYMMDD)


def get_quarter_end_impl(date: str) -> str:
    """获取季度末"""
    dt = parse_date(date)
    quarter = (dt.month - 1) // 3 + 1
    # 下一季度第一天 - 1天
    if quarter == 4:
        next_quarter_start = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        next_start_month = {1: 4, 2: 7, 3: 10, 4: 1}[quarter]
        next_quarter_start = dt.replace(month=next_start_month, day=1)
    last_day = next_quarter_start - timedelta(days=1)
    return last_day.strftime(FMT_YYYYMMDD)


def get_week_start_impl(date: str) -> str:
    """获取周一"""
    dt = parse_date(date)
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime(FMT_YYYYMMDD)


def get_week_end_impl(date: str) -> str:
    """获取周日"""
    dt = parse_date(date)
    sunday = dt + timedelta(days=(6 - dt.weekday()))
    return sunday.strftime(FMT_YYYYMMDD)


def is_before_impl(date1: str, date2: str) -> bool:
    """date1 是否在 date2 之前"""
    dt1 = parse_date(date1)
    dt2 = parse_date(date2)
    return dt1 < dt2


def is_after_impl(date1: str, date2: str) -> bool:
    """date1 是否在 date2 之后"""
    dt1 = parse_date(date1)
    dt2 = parse_date(date2)
    return dt1 > dt2


def is_same_impl(date1: str, date2: str) -> bool:
    """是否同一天"""
    dt1 = parse_date(date1)
    dt2 = parse_date(date2)
    return dt1.date() == dt2.date()
