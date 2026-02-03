#!/usr/bin/env python3
"""
日期工具类 - 提供统一的日期转换和处理方法

默认日期格式：YYYYMMDD 字符串（如 "20240101"）
"""
from datetime import datetime, timedelta
from enum import Enum

from core.infra.project_context import ConfigManager


class DateFormat(Enum):
    """
    日期格式枚举 - 定义系统内使用的标准输出格式
    - DAY: YYYYMMDD（如 "20240101"）
    - MONTH: YYYYMM（如 "202401"）
    - QUARTER: YYYYQ[1-4]（如 "2024Q1"）
    - NONE: 不标准化
    """
    DAY = "day"
    MONTH = "month"
    QUARTER = "quarter"
    NONE = "none"


class DateUtils:
    """日期工具类 - 默认格式 YYYYMMDD"""
    
    # 格式常量
    FMT_YYYYMMDD = '%Y%m%d'
    FMT_YYYY_MM_DD = '%Y-%m-%d'
    FMT_DATETIME = '%Y-%m-%d %H:%M:%S'
    
    # 默认值（兼容旧引用）
    DATE_FORMAT_YYYYMMDD = FMT_YYYYMMDD
    DATE_FORMAT_YYYY_MM_DD = FMT_YYYY_MM_DD
    DATE_FORMAT_YYYY_MM_DD_HH_MM_SS = FMT_DATETIME
    DEFAULT_FORMAT = FMT_YYYYMMDD
    DEFAULT_START_DATE = ConfigManager.get_default_start_date()

    # ==================== string to format ====================

    @staticmethod
    def to_format(date_str: str, fmt: str = None) -> str:
        """将日期字符串格式化为默认格式"""
        return datetime.strptime(date_str, fmt or DateUtils.FMT_YYYYMMDD).strftime(DateUtils.FMT_YYYYMMDD)

    @staticmethod
    def to_default_format(date_str: str) -> str:
        """将日期字符串格式化为默认格式"""
        return datetime.strptime(date_str, DateUtils.FMT_YYYYMMDD).strftime(DateUtils.FMT_YYYYMMDD)


    # ==================== 解析 ====================

    @staticmethod
    def parse(date_str: str, fmt: str = None) -> datetime:
        """解析日期字符串为 datetime，默认 YYYYMMDD"""
        return datetime.strptime(date_str, fmt or DateUtils.FMT_YYYYMMDD)


    # ==================== quick APIs ====================

    # ==================== days ====================

    @staticmethod
    def get_today_str(fmt: str = None) -> str:
        """获取当前日期字符串，默认 YYYYMMDD"""
        return datetime.now().strftime(fmt or DateUtils.FMT_YYYYMMDD)

    @staticmethod
    def is_today(date_str: str) -> bool:
        """判断日期是否为今天"""
        return DateUtils.to_default_format(date_str) == DateUtils.get_today_str()


    @staticmethod
    def is_before_or_same_day(date1: str, date2: str) -> bool:
        """判断日期是否在另一个日期之前或同一天"""
        return DateUtils.parse(date1).date() <= DateUtils.parse(date2).date()

    @staticmethod
    def get_duration_in_days(date1: str, date2: str) -> int:
        """计算两个日期之间的天数差"""
        return (DateUtils.parse(date2) - DateUtils.parse(date1)).days

    @staticmethod
    def get_duration_by_term(term: str, date1: str, date2: str) -> int:
        """按 term 计算周期差：daily=天数, weekly=周数, monthly=月数"""
        days = DateUtils.get_duration_in_days(date1, date2)
        if term in ("daily", "day", "date"):
            return days
        if term in ("weekly", "week"):
            return days // 7
        if term in ("monthly", "month"):
            return days // 30

    @staticmethod
    def add_days(date_str: str, days: int) -> str:
        """加 N 天"""
        return DateUtils.to_format(DateUtils.parse(date_str) + timedelta(days=days))

    @staticmethod
    def sub_days(date_str: str, days: int) -> str:
        """减 N 天"""
        return DateUtils.to_format(DateUtils.parse(date_str) - timedelta(days=days))

    @staticmethod
    def get_previous_day(date_str: str) -> str:
        """前一天"""
        return DateUtils.sub_days(date_str, 1)

    @staticmethod
    def get_next_date(date_str: str) -> str:
        """下一天"""
        return DateUtils.add_days(date_str, 1)

    @staticmethod
    def get_date_str_before_days(base_date_str: str, delta_days: int) -> str:
        """获取 N 天前的日期"""
        return DateUtils.sub_days(base_date_str, delta_days)

    @staticmethod
    def get_date_str_after_days(base_date_str: str, delta_days: int) -> str:
        """获取 N 天后的日期"""
        return DateUtils.add_days(base_date_str, delta_days)


    # ==================== week ====================

    @staticmethod
    def get_week_start_date(date_str: str) -> str:
        """获取日期所在的周的开始日期"""
        return DateUtils.get_previous_day(DateUtils.parse(date_str).strftime("%Y%m%d"))

    @staticmethod
    def get_week_end_date(date_str: str) -> str:
        """获取日期所在的周的结束日期"""
        return DateUtils.get_next_date(DateUtils.parse(date_str).strftime("%Y%m%d"))

    @staticmethod
    def get_previous_week_end(date_str: str) -> str:
        """获取日期所在周的前一周周日"""
        return DateUtils.get_previous_day(DateUtils.get_week_start_date(date_str))



    # ==================== month ====================

    @staticmethod
    def get_previous_month_end(date_str: str) -> str:
        """获取日期所在月的前一个月最后一天"""
        return DateUtils.get_previous_day(DateUtils.get_month_start_date(date_str))

    @staticmethod
    def get_next_month_start(date_str: str) -> str:
        """获取日期所在月的下一个月第一天"""
        return DateUtils.get_next_date(DateUtils.get_month_end_date(date_str))


    # ==================== quarter ====================
    @staticmethod
    def date_to_quarter(date_str: str) -> str:
        """YYYYMMDD -> YYYYQ[1-4]"""
        if not date_str or len(date_str) != 8:
            raise ValueError(f"日期格式错误: {date_str}，应为 YYYYMMDD")
        y, m = int(date_str[:4]), int(date_str[4:6])
        q = (m - 1) // 3 + 1
        return f"{y}Q{q}"

    @staticmethod
    def quarter_to_date(date_str: str, is_start: bool = True) -> str:
        """获取日期对应的季度"""
        if not date_str or len(date_str) != 6 or date_str[4] != 'Q':
            raise ValueError(f"季度格式错误: {date_str}")
        y, q = int(date_str[:4]), int(date_str[5])
        if q < 1 or q > 4:
            raise ValueError(f"季度值错误: {q}")
        if is_start:
            return f"{y}{q:02d}01"
        else:   
            next_quarter = q + 1 if q < 4 else 1
            return DateUtils.sub_days(f"{y}{next_quarter:02d}01", 1)
        
    @staticmethod
    def get_quarter_start_date(quarter_str: str) -> str:
        """获取季度开始日期"""
        return DateUtils.quarter_to_date(quarter_str, is_start=True)

    @staticmethod
    def get_quarter_end_date(quarter_str: str) -> str:
        """获取季度结束日期"""
        return DateUtils.quarter_to_date(quarter_str, is_start=False)

    @staticmethod
    def get_current_quarter() -> str:
        """获取当前季度"""
        return DateUtils.date_to_quarter(DateUtils.get_today_str())
    
    @staticmethod
    def get_previous_quarter(quarter_str: str) -> str:
        """获取上一个季度"""
        return DateUtils.get_previous_day(DateUtils.quarter_to_date(quarter_str, is_start=False))
    
    @staticmethod
    def get_next_quarter(quarter_str: str) -> str:
        """获取下一个季度"""
        return DateUtils.get_next_date(DateUtils.quarter_to_date(quarter_str, is_start=True))