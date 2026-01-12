#!/usr/bin/env python3
"""
PriceFactorSimulator 的计算辅助函数

从 legacy AnalyzerService 迁移过来的工具函数，用于：
- 日期解析
- 比率/百分比计算
- 年化收益率计算
"""

from datetime import datetime
from typing import Optional


def parse_yyyymmdd(date_str: str) -> Optional[datetime]:
    """
    安全解析 YYYYMMDD 格式的日期字符串，失败返回 None。
    
    Args:
        date_str: YYYYMMDD 格式的日期字符串（如 "20240112"）
        
    Returns:
        datetime 对象，解析失败返回 None
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), '%Y%m%d')
    except Exception:
        return None


def to_ratio(numerator: float, denominator: float, decimals: int = 2) -> float:
    """
    计算比率并按指定小数位四舍五入。只在分母为0时返回0.0；允许负值。
    
    Args:
        numerator: 分子
        denominator: 分母
        decimals: 小数位数（默认2位）
        
    Returns:
        比率值（小数形式，如 0.1 表示 10%）
    """
    try:
        if denominator == 0:
            return 0.0
        value = float(numerator) / float(denominator)
        return round(value, decimals)
    except ZeroDivisionError:
        return 0.0
    except Exception:
        return 0.0


def to_percent(numerator: float, denominator: float, decimals: int = 2) -> float:
    """
    与 to_ratio 相同的入参，输出为百分比（ratio*100）。仅分母为0时返回0.0，允许负值。
    
    Args:
        numerator: 分子
        denominator: 分母
        decimals: 小数位数（默认2位）
        
    Returns:
        百分比值（如 10.0 表示 10%）
    """
    try:
        if denominator == 0:
            return 0.0
        value = float(numerator) / float(denominator)
        return round(value * 100.0, decimals)
    except ZeroDivisionError:
        return 0.0
    except Exception:
        return 0.0


def get_annual_return(profit_rate: float, duration_in_days: int, is_trading_days: bool = False) -> float:
    """
    计算年化收益率（使用复利公式）
    
    Args:
        profit_rate: 总收益率（小数形式，如0.1表示10%）
        duration_in_days: 投资持续天数
        is_trading_days: 是否使用交易日计算（True: 250天/年，False: 365天/年）
        
    Returns:
        float: 年化收益率（小数形式，如0.15表示15%）
    """
    if is_trading_days:
        years = duration_in_days / 250.0
    else:
        years = duration_in_days / 365.0

    if duration_in_days <= 0 or profit_rate == 0:
        return 0.0
    
    if years <= 0:
        return 0.0
    
    # 使用复利公式：年化收益率 = ((1 + 总收益率) ^ (1/年数)) - 1
    annual_return = ((1 + profit_rate) ** (1 / years)) - 1
    return annual_return
