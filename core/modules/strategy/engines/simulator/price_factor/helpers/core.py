#!/usr/bin/env python3
from datetime import datetime
from typing import Optional
import json


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, float):
            if obj != obj or obj in (float("inf"), float("-inf")):
                return None
            return obj
        if isinstance(obj, int):
            return int(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def parse_yyyymmdd(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), "%Y%m%d")
    except Exception:
        return None


def to_ratio(numerator: float, denominator: float, decimals: int = 2) -> float:
    try:
        if denominator == 0:
            return 0.0
        return round(float(numerator) / float(denominator), decimals)
    except Exception:
        return 0.0


def to_percent(numerator: float, denominator: float, decimals: int = 2) -> float:
    try:
        if denominator == 0:
            return 0.0
        return round(float(numerator) / float(denominator) * 100.0, decimals)
    except Exception:
        return 0.0


def get_annual_return(profit_rate: float, duration_in_days: int, is_trading_days: bool = False) -> float:
    years = duration_in_days / (250.0 if is_trading_days else 365.0)
    if duration_in_days <= 0 or profit_rate == 0 or years <= 0:
        return 0.0
    if profit_rate <= -1.0:
        return -1.0
    base = 1.0 + float(profit_rate)
    if base <= 0.0:
        return -1.0
    try:
        value = (base ** (1.0 / years)) - 1.0
    except (OverflowError, ValueError, ZeroDivisionError):
        return 0.0
    if isinstance(value, complex) or value != value or value in (float("inf"), float("-inf")):
        return 0.0
    return float(value)


__all__ = ["DateTimeEncoder", "parse_yyyymmdd", "to_ratio", "to_percent", "get_annual_return"]
