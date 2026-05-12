#!/usr/bin/env python3
from datetime import datetime
from typing import Optional
import json


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (int, float)):
            return float(obj) if isinstance(obj, float) else int(obj)
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
    return ((1 + profit_rate) ** (1 / years)) - 1


__all__ = ["DateTimeEncoder", "parse_yyyymmdd", "to_ratio", "to_percent", "get_annual_return"]
