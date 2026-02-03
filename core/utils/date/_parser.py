"""
日期解析和格式转换模块（内部使用）

职责：处理各种输入格式的解析和标准化，只负责格式转换，不做计算。
"""
from datetime import datetime, date
from typing import Any, Optional, Union

from core.utils.utils import Utils
from core.utils.date._constants import FMT_YYYYMMDD, FMT_YYYY_MM_DD, DEFAULT_FORMAT


def is_date(obj: Any) -> bool:
    """判断是否为 date 对象"""
    return isinstance(obj, date) and not isinstance(obj, datetime)


def normalize_date_str(date_str: Optional[str]) -> Optional[str]:
    """
    将常见日期字符串标准化为 YYYYMMDD。
    
    支持：
    - YYYYMMDD
    - YYYY-MM-DD
    
    Returns:
        str: YYYYMMDD 格式，失败返回 None
    """
    if not date_str:
        return None
    s = str(date_str).strip()
    if not s:
        return None

    # 已是纯 8 位数字
    if len(s) == 8 and s.isdigit():
        return s

    # YYYY-MM-DD
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            dt = datetime.strptime(s, FMT_YYYY_MM_DD)
            return dt.strftime(FMT_YYYYMMDD)
        except ValueError:
            return None

    return None


def parse_quarter_str(quarter_str: str) -> Optional[tuple]:
    """
    解析季度字符串为 (year, quarter)
    
    Args:
        quarter_str: YYYYQ1 或 YYYYMMQ1 格式
    
    Returns:
        tuple: (year, quarter) 或 None
    """
    if not quarter_str:
        return None
    
    s = str(quarter_str).strip()
    
    # YYYYQ1 格式
    if len(s) == 6 and s[4] == "Q":
        try:
            y, q = int(s[:4]), int(s[5])
            if 1 <= q <= 4:
                return (y, q)
        except (ValueError, IndexError):
            pass
    
    # YYYYMMQ1 格式
    if len(s) == 8 and s[6] == "Q":
        try:
            y, q = int(s[:4]), int(s[7])
            if 1 <= q <= 4:
                return (y, q)
        except (ValueError, IndexError):
            pass
    
    return None


def quarter_to_date_str(quarter_str: str, is_start: bool = True) -> Optional[str]:
    """
    季度字符串转日期字符串
    
    Args:
        quarter_str: YYYYQ1 格式
        is_start: True=季度第一天，False=季度最后一天
    
    Returns:
        str: YYYYMMDD 格式，失败返回 None
    """
    parsed = parse_quarter_str(quarter_str)
    if not parsed:
        return None
    
    y, q = parsed
    
    # 每个季度起始月份：1,4,7,10
    start_month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
    
    if is_start:
        return f"{y}{start_month:02d}01"
    
    # 结束日期 = 下一季度第一天 - 1
    if q < 4:
        next_y, next_q = y, q + 1
    else:
        next_y, next_q = y + 1, 1
    next_start_month = {1: 1, 2: 4, 3: 7, 4: 10}[next_q]
    from datetime import timedelta
    first_next = datetime(next_y, next_start_month, 1)
    last_day = first_next - timedelta(days=1)
    return last_day.strftime(FMT_YYYYMMDD)


def date_to_quarter_str(date_str: str) -> str:
    """
    日期字符串转季度字符串
    
    Args:
        date_str: YYYYMMDD 格式
    
    Returns:
        str: YYYYQ1 格式
    """
    if not date_str or len(date_str) != 8:
        raise ValueError(f"日期格式错误: {date_str}，应为 YYYYMMDD")
    
    y, m = int(date_str[:4]), int(date_str[4:6])
    q = (m - 1) // 3 + 1
    return f"{y}Q{q}"


def to_format_impl(input: Any, fmt: str = DEFAULT_FORMAT) -> Optional[str]:
    """
    通用格式化实现：将任意输入转换为指定格式的字符串
    
    Args:
        input: 可以是 datetime, date, str
        fmt: 目标格式
    
    Returns:
        str: 格式化后的字符串，失败返回 None
    """
    if input is None:
        return None
    
    # datetime/date 对象
    if Utils.is_datetime(input) or is_date(input):
        try:
            return input.strftime(fmt)
        except Exception:
            return None
    
    # 字符串
    if Utils.is_string(input):
        s = str(input).strip()
        if not s:
            return None
        
        # 先尝试标准化为 YYYYMMDD
        normalized = normalize_date_str(s)
        if normalized:
            # 如果目标格式就是 YYYYMMDD，直接返回
            if fmt == FMT_YYYYMMDD:
                return normalized
            # 否则转换格式
            try:
                dt = datetime.strptime(normalized, FMT_YYYYMMDD)
                return dt.strftime(fmt)
            except Exception:
                return None
        
        # 尝试解析为 YYYYMM（视为当月第一天）
        if len(s) == 6 and s.isdigit():
            try:
                y, m = int(s[:4]), int(s[4:6])
                if 1 <= m <= 12:
                    dt = datetime(y, m, 1)
                    return dt.strftime(fmt)
            except Exception:
                pass
        
        # 尝试解析季度格式
        quarter_parsed = parse_quarter_str(s)
        if quarter_parsed:
            date_str = quarter_to_date_str(s, is_start=True)
            if date_str:
                try:
                    dt = datetime.strptime(date_str, FMT_YYYYMMDD)
                    return dt.strftime(fmt)
                except Exception:
                    pass
    
    return None


def normalize_impl(input: Any, fmt: str = DEFAULT_FORMAT) -> Optional[str]:
    """
    通用标准化实现：将任意输入标准化为指定格式（智能识别）
    
    Args:
        input: 可以是 datetime, date, str, YYYYMM, YYYYQ1 等
        fmt: 目标格式（默认 YYYYMMDD）
    
    Returns:
        str: 标准化后的字符串，失败返回 None
    """
    return to_format_impl(input, fmt)


def datetime_to_format_impl(dt: datetime, fmt: str = DEFAULT_FORMAT) -> str:
    """
    明确：datetime → str
    
    Raises:
        ValueError: 如果输入不是 datetime
    """
    if not Utils.is_datetime(dt):
        raise ValueError(f"输入必须是 datetime 对象，得到: {type(dt)}")
    return dt.strftime(fmt)


def date_to_format_impl(d: date, fmt: str = DEFAULT_FORMAT) -> str:
    """
    明确：date → str
    
    Raises:
        ValueError: 如果输入不是 date
    """
    if not is_date(d):
        raise ValueError(f"输入必须是 date 对象，得到: {type(d)}")
    return d.strftime(fmt)


def str_to_format_impl(date_str: str, to_fmt: str, from_fmt: Optional[str] = None) -> Optional[str]:
    """
    明确：str → str（格式转换）
    
    Args:
        date_str: 源日期字符串
        to_fmt: 目标格式
        from_fmt: 源格式（None 时自动识别）
    
    Returns:
        str: 转换后的字符串，失败返回 None
    """
    if not Utils.is_string(date_str):
        return None
    
    # 如果指定了源格式，直接转换
    if from_fmt:
        try:
            dt = datetime.strptime(date_str, from_fmt)
            return dt.strftime(to_fmt)
        except Exception:
            return None
    
    # 否则先标准化为 YYYYMMDD，再转换
    normalized = normalize_date_str(date_str)
    if normalized:
        try:
            dt = datetime.strptime(normalized, FMT_YYYYMMDD)
            return dt.strftime(to_fmt)
        except Exception:
            pass
    
    # 尝试其他格式（YYYYMM, YYYYQ1）
    result = to_format_impl(date_str, to_fmt)
    return result


def normalize_str_impl(date_str: str, fmt: str = DEFAULT_FORMAT) -> Optional[str]:
    """
    明确：str → str（标准化）
    
    支持自动识别：YYYYMMDD, YYYY-MM-DD, YYYYMM, YYYYQ1 等
    """
    if not Utils.is_string(date_str):
        return None
    return normalize_impl(date_str, fmt)


def normalize_datetime_impl(dt: datetime, fmt: str = DEFAULT_FORMAT) -> str:
    """明确：datetime → str（标准化）"""
    return datetime_to_format_impl(dt, fmt)


def normalize_date_impl(d: date, fmt: str = DEFAULT_FORMAT) -> str:
    """明确：date → str（标准化）"""
    return date_to_format_impl(d, fmt)


def str_to_datetime_impl(date_str: str, fmt: Optional[str] = None) -> datetime:
    """
    明确：str → datetime
    
    Args:
        date_str: 日期字符串
        fmt: 源格式（None 时自动识别）
    
    Returns:
        datetime: 解析后的 datetime 对象
    
    Raises:
        ValueError: 解析失败时抛出
    """
    if not Utils.is_string(date_str):
        raise ValueError(f"输入必须是字符串，得到: {type(date_str)}")
    
    # 如果指定了格式，直接解析
    if fmt:
        return datetime.strptime(date_str, fmt)
    
    # 否则先标准化
    normalized = normalize_date_str(date_str)
    if normalized:
        return datetime.strptime(normalized, FMT_YYYYMMDD)
    
    # 尝试其他格式
    result = to_format_impl(date_str, FMT_YYYYMMDD)
    if result:
        return datetime.strptime(result, FMT_YYYYMMDD)
    
    raise ValueError(f"无法解析日期字符串: {date_str}")
