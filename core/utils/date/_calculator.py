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


def get_period_end_impl(date: str, term: str) -> Optional[str]:
    """
    获取某个日期所在周期的结束日期（自然日）。
    
    用于检查周期是否完整结束，避免获取未完成周期的"脏数据"。
    
    支持的周期类型：
        - weekly: 返回该日期所在周的周日
        - monthly: 返回该日期所在月的最后一天
        - quarterly: 返回该日期所在季度的最后一天（0331, 0630, 0930, 1231）
        - yearly: 返回该日期所在年的最后一天（1231）
    
    Args:
        date: 日期（YYYYMMDD格式）
        term: 周期类型（"weekly", "monthly", "quarterly", "yearly"）
    
    Returns:
        周期结束日期（YYYYMMDD格式），如果term不支持则返回None
    """
    term_lower = term.lower()
    try:
        if term_lower == "weekly":
            return get_week_end_impl(date)
        elif term_lower == "monthly":
            return get_month_end_impl(date)
        elif term_lower == "quarterly":
            return get_quarter_end_impl(date)
        elif term_lower == "yearly":
            return f"{date[:4]}1231"
        else:
            return None
    except Exception:
        return None


def get_previous_period_end_impl(current_date: str, term: str) -> Optional[str]:
    """
    获取上一周期的结束日期（自然日）。
    
    用于计算end_date，确保只获取已完整结束的周期数据，避免获取当前未完成周期的"脏数据"。
    
    支持的周期类型：
        - weekly: 返回上一周的周日（A股的周交易日最后一天是周日）
        - monthly: 返回上一月的最后一天
        - quarterly: 返回上一季度的最后一天
        - yearly: 返回上一年的最后一天（1231）
    
    Args:
        current_date: 当前日期（YYYYMMDD格式），通常是latest_completed_trading_date
        term: 周期类型（"weekly", "monthly", "quarterly", "yearly"）
    
    Returns:
        上一周期的结束日期（YYYYMMDD格式），如果term不支持则返回None
    """
    term_lower = term.lower()
    try:
        if term_lower == "weekly":
            # A股的周交易日最后一天是周日，所以找到上一周的周日
            current_week_start = get_week_start_impl(current_date)
            # 上一周的周日 = 本周周一往前推1天
            prev_week_sunday = (parse_date(current_week_start) - timedelta(days=1)).strftime(FMT_YYYYMMDD)
            return prev_week_sunday
        elif term_lower == "monthly":
            # 找到上一月的结束日期
            current_month_start = get_month_start_impl(current_date)
            prev_month_end = (parse_date(current_month_start) - timedelta(days=1)).strftime(FMT_YYYYMMDD)
            return prev_month_end
        elif term_lower == "quarterly":
            # 找到上一季度的结束日期
            dt = parse_date(current_date)
            quarter = (dt.month - 1) // 3 + 1
            if quarter == 1:
                # 上一季度是去年Q4
                return f"{dt.year - 1}1231"
            elif quarter == 2:
                return f"{dt.year}0331"
            elif quarter == 3:
                return f"{dt.year}0630"
            else:  # quarter == 4
                return f"{dt.year}0930"
        elif term_lower == "yearly":
            # 上一年的结束日期
            year = int(current_date[:4])
            return f"{year - 1}1231"
        else:
            return None
    except Exception:
        return None
