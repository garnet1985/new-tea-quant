"""
周期处理模块（内部使用）

职责：周期的加减、比较、转换（最复杂的逻辑），所有周期值用字符串表示。
"""
from datetime import datetime, timedelta
from typing import List, Optional

from core.utils.date._constants import PERIOD_DAY, PERIOD_MONTH, PERIOD_QUARTER, PERIOD_YEAR, FMT_YYYYMMDD


def normalize_date_str(date_str: Optional[str]) -> Optional[str]:
    """内部辅助：标准化日期字符串"""
    if not date_str:
        return None
    s = str(date_str).strip()
    if not s:
        return None
    if len(s) == 8 and s.isdigit():
        return s
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.strftime(FMT_YYYYMMDD)
        except ValueError:
            return None
    return None


def parse_quarter_str(quarter_str: str) -> Optional[tuple]:
    """内部辅助：解析季度字符串"""
    if not quarter_str:
        return None
    s = str(quarter_str).strip()
    if len(s) == 6 and s[4] == "Q":
        try:
            y, q = int(s[:4]), int(s[5])
            if 1 <= q <= 4:
                return (y, q)
        except (ValueError, IndexError):
            pass
    if len(s) == 8 and s[6] == "Q":
        try:
            y, q = int(s[:4]), int(s[7])
            if 1 <= q <= 4:
                return (y, q)
        except (ValueError, IndexError):
            pass
    return None


def date_to_quarter_str(date_str: str) -> str:
    """内部辅助：日期转季度"""
    if not date_str or len(date_str) != 8:
        raise ValueError(f"日期格式错误: {date_str}，应为 YYYYMMDD")
    y, m = int(date_str[:4]), int(date_str[4:6])
    q = (m - 1) // 3 + 1
    return f"{y}Q{q}"


def quarter_to_date_str(quarter_str: str, is_start: bool = True) -> Optional[str]:
    """内部辅助：季度转日期"""
    parsed = parse_quarter_str(quarter_str)
    if not parsed:
        return None
    y, q = parsed
    start_month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
    if is_start:
        return f"{y}{start_month:02d}01"
    if q < 4:
        next_y, next_q = y, q + 1
    else:
        next_y, next_q = y + 1, 1
    next_start_month = {1: 1, 2: 4, 3: 7, 4: 10}[next_q]
    first_next = datetime(next_y, next_start_month, 1)
    last_day = first_next - timedelta(days=1)
    return last_day.strftime(FMT_YYYYMMDD)


def add_days_impl(date: str, days: int) -> str:
    """内部辅助：日期加法"""
    normalized = normalize_date_str(date)
    if not normalized:
        raise ValueError(f"日期格式错误: {date}")
    dt = datetime.strptime(normalized, FMT_YYYYMMDD)
    result = dt + timedelta(days=days)
    return result.strftime(FMT_YYYYMMDD)


def normalize_period_type(period_type: str) -> str:
    """
    规范化周期类型字符串
    
    Examples:
        "daily" -> "day"
        "monthly" -> "month"
        "quarterly" -> "quarter"
    """
    if not period_type:
        return PERIOD_DAY
    
    v = str(period_type).lower()
    if v in ("daily", "day", "date"):
        return PERIOD_DAY
    if v in ("weekly", "week"):
        return "week"
    if v in ("monthly", "month"):
        return PERIOD_MONTH
    if v in ("quarterly", "quarter"):
        return PERIOD_QUARTER
    if v in ("yearly", "year"):
        return "year"
    
    return v


def detect_period_type(period_str: str) -> str:
    """
    自动识别周期字符串类型
    
    Examples:
        "202401" -> "month"
        "2024Q1" -> "quarter"
        "20240115" -> "day"
        "2024" -> "year"
    """
    if not period_str:
        return PERIOD_DAY
    
    s = str(period_str).strip()
    
    # 季度格式
    if "Q" in s and (len(s) == 6 or len(s) == 8):
        return PERIOD_QUARTER
    
    # 年份格式
    if len(s) == 4 and s.isdigit():
        return "year"
    
    # 月份格式
    if len(s) == 6 and s.isdigit():
        return PERIOD_MONTH
    
    # 日期格式
    if len(s) == 8 and s.isdigit():
        return PERIOD_DAY
    
    return PERIOD_DAY


def to_period_str_impl(date: str, period_type: str) -> str:
    """
    将日期转换为周期字符串
    
    Args:
        date: YYYYMMDD 格式
        period_type: PERIOD_DAY/MONTH/QUARTER/YEAR
    
    Returns:
        str: 周期字符串
        - DAY -> "20240115"
        - MONTH -> "202401"
        - QUARTER -> "2024Q1"
        - YEAR -> "2024"
    """
    normalized = normalize_date_str(date)
    if not normalized:
        raise ValueError(f"日期格式错误: {date}，应为 YYYYMMDD")
    
    period_type = normalize_period_type(period_type)
    
    if period_type == PERIOD_DAY:
        return normalized
    if period_type == PERIOD_MONTH:
        return normalized[:6]
    if period_type == PERIOD_QUARTER:
        return date_to_quarter_str(normalized)
    if period_type == "year":
        return normalized[:4]
    
    return normalized


def from_period_str_impl(period_str: str, period_type: str, is_start: bool = True) -> str:
    """
    将周期字符串转换为日期
    
    Args:
        period_str: 周期字符串
        period_type: PERIOD_DAY/MONTH/QUARTER/YEAR
        is_start: True=起始日，False=结束日
    
    Returns:
        str: YYYYMMDD 格式
    """
    period_type = normalize_period_type(period_type)
    
    if period_type == PERIOD_DAY:
        normalized = normalize_date_str(period_str)
        if not normalized:
            raise ValueError(f"日期格式错误: {period_str}")
        return normalized
    
    if period_type == PERIOD_MONTH:
        if len(period_str) != 6 or not period_str.isdigit():
            raise ValueError(f"月份格式错误: {period_str}，应为 YYYYMM")
        if is_start:
            return f"{period_str}01"
        # 月末
        y, m = int(period_str[:4]), int(period_str[4:6])
        if m == 12:
            next_y, next_m = y + 1, 1
        else:
            next_y, next_m = y, m + 1
        from datetime import datetime, timedelta
        first_next = datetime(next_y, next_m, 1)
        last_day = first_next - timedelta(days=1)
        return last_day.strftime(FMT_YYYYMMDD)
    
    if period_type == PERIOD_QUARTER:
        result = quarter_to_date_str(period_str, is_start=is_start)
        if not result:
            raise ValueError(f"季度格式错误: {period_str}，应为 YYYYQ1")
        return result
    
    if period_type == "year":
        if len(period_str) != 4 or not period_str.isdigit():
            raise ValueError(f"年份格式错误: {period_str}，应为 YYYY")
        if is_start:
            return f"{period_str}0101"
        # 年末
        return f"{period_str}1231"
    
    raise ValueError(f"不支持的周期类型: {period_type}")


def add_periods_impl(period: str, count: int, period_type: str) -> str:
    """
    周期加法
    
    Examples:
        add_periods("202401", 3, PERIOD_MONTH) -> "202404"
        add_periods("2024Q1", 2, PERIOD_QUARTER) -> "2024Q3"
    """
    period_type = normalize_period_type(period_type)
    
    if period_type == PERIOD_DAY:
        return add_days_impl(period, count)
    
    if period_type == PERIOD_MONTH:
        if len(period) != 6 or not period.isdigit():
            raise ValueError(f"月份格式错误: {period}")
        y, m = int(period[:4]), int(period[4:6])
        m += count
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        return f"{y}{m:02d}"
    
    if period_type == PERIOD_QUARTER:
        parsed = parse_quarter_str(period)
        if not parsed:
            raise ValueError(f"季度格式错误: {period}")
        y, q = parsed
        q += count
        while q > 4:
            q -= 4
            y += 1
        while q < 1:
            q += 4
            y -= 1
        return f"{y}Q{q}"
    
    if period_type == "year":
        if len(period) != 4 or not period.isdigit():
            raise ValueError(f"年份格式错误: {period}")
        y = int(period) + count
        return f"{y}"
    
    raise ValueError(f"不支持的周期类型: {period_type}")


def sub_periods_impl(period: str, count: int, period_type: str) -> str:
    """周期减法"""
    return add_periods_impl(period, -count, period_type)


def diff_periods_impl(period1: str, period2: str, period_type: str) -> int:
    """
    计算周期差值
    
    Returns:
        int: period2 - period1 的周期数
    """
    period_type = normalize_period_type(period_type)
    
    if period_type == PERIOD_DAY:
        from core.utils.date._calculator import diff_days_impl
        return diff_days_impl(period1, period2)
    
    if period_type == PERIOD_MONTH:
        if len(period1) != 6 or len(period2) != 6:
            raise ValueError("月份格式错误")
        y1, m1 = int(period1[:4]), int(period1[4:6])
        y2, m2 = int(period2[:4]), int(period2[4:6])
        return (y2 - y1) * 12 + (m2 - m1)
    
    if period_type == PERIOD_QUARTER:
        p1 = parse_quarter_str(period1)
        p2 = parse_quarter_str(period2)
        if not p1 or not p2:
            raise ValueError("季度格式错误")
        y1, q1 = p1
        y2, q2 = p2
        return (y2 - y1) * 4 + (q2 - q1)
    
    if period_type == "year":
        if len(period1) != 4 or len(period2) != 4:
            raise ValueError("年份格式错误")
        return int(period2) - int(period1)
    
    raise ValueError(f"不支持的周期类型: {period_type}")


def is_period_before_impl(period1: str, period2: str, period_type: str) -> bool:
    """period1 是否在 period2 之前"""
    return diff_periods_impl(period1, period2, period_type) < 0


def is_period_after_impl(period1: str, period2: str, period_type: str) -> bool:
    """period1 是否在 period2 之后"""
    return diff_periods_impl(period1, period2, period_type) > 0


def generate_period_range_impl(start: str, end: str, period_type: str) -> List[str]:
    """
    生成周期序列
    
    Examples:
        generate_period_range("202401", "202404", PERIOD_MONTH)
        -> ["202401", "202402", "202403", "202404"]
    """
    period_type = normalize_period_type(period_type)
    result = []
    current = start
    
    # 确保 start <= end
    if is_period_after_impl(start, end, period_type):
        return []
    
    while True:
        result.append(current)
        if current == end:
            break
        current = add_periods_impl(current, 1, period_type)
        if is_period_after_impl(current, end, period_type):
            break
    
    return result


# 季度专用便捷方法
def add_quarters_impl(quarter: str, count: int) -> str:
    """季度加法（便捷方法）"""
    return add_periods_impl(quarter, count, PERIOD_QUARTER)


def sub_quarters_impl(quarter: str, count: int) -> str:
    """季度减法（便捷方法）"""
    return sub_periods_impl(quarter, count, PERIOD_QUARTER)


def diff_quarters_impl(quarter1: str, quarter2: str) -> int:
    """季度差值（便捷方法）"""
    return diff_periods_impl(quarter1, quarter2, PERIOD_QUARTER)


def get_period_sort_key_impl(period_str: str, period_type: str) -> str:
    """
    获取排序键（用于排序）
    
    将周期字符串转换为日期作为排序键
    """
    return from_period_str_impl(period_str, period_type, is_start=True)
