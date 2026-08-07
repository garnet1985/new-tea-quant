#!/usr/bin/env python3
"""
日期工具类 - 提供统一的日期转换和处理方法

统一对外接口，所有功能都通过 DateUtils 类暴露。
内部模块化实现，用户无需了解内部结构。
"""
from datetime import datetime, date
from typing import Any, Optional, List

# 内部实现模块（别名避免与参数名 period 冲突）
from core.infra.utils.core.date import calculator as date_calculator
from core.infra.utils.core.date import constants as date_constants
from core.infra.utils.core.date import parser as date_parser
from core.infra.utils.core.date import period as date_period


class DateUtils:
    """
    日期工具类 - 统一对外接口
    
    所有日期时间相关的功能都通过本类提供，内部委托给专门模块实现。
    """
    
    # ==================== 常量定义 ====================
    
    # 格式化字符串常量
    FMT_YYYYMMDD = date_constants.FMT_YYYYMMDD
    FMT_YYYY_MM_DD = date_constants.FMT_YYYY_MM_DD
    FMT_YYYYMM = date_constants.FMT_YYYYMM
    FMT_YYYYQ = date_constants.FMT_YYYYQ
    FMT_DATETIME = date_constants.FMT_DATETIME
    
    # 周期类型常量
    PERIOD_DAY = date_constants.PERIOD_DAY
    PERIOD_WEEK = date_constants.PERIOD_WEEK
    PERIOD_MONTH = date_constants.PERIOD_MONTH
    PERIOD_QUARTER = date_constants.PERIOD_QUARTER
    PERIOD_YEAR = date_constants.PERIOD_YEAR
    
    # 默认值
    DEFAULT_FORMAT = date_constants.DEFAULT_FORMAT

    # 无界查询上界（YYYYMMDD）
    QUERY_DATE_RANGE_MAX = date_constants.QUERY_DATE_RANGE_MAX

    @staticmethod
    def get_query_date_range_min() -> str:
        """
        无界查询下界（YYYYMMDD）：与 `core/default_config/data.json` 中 `default_start_date` 一致；
        配置缺失或无法标准化时回退到内部兜底常量。
        """
        from core.infra.project_context import ProjectContext

        raw = ProjectContext.config.get_default_start_date()
        if raw:
            n = DateUtils.normalize_str(str(raw))
            if n:
                return n
        return date_constants.QUERY_DATE_RANGE_FALLBACK_MIN

    # ==================== 格式转换（通用方法）====================
    
    @staticmethod
    def to_format(input: Any, fmt: str = None) -> Optional[str]:
        """
        通用格式化：将任意输入转换为指定格式的字符串
        
        Args:
            input: 可以是 datetime, date, str（自动识别类型）
            fmt: 目标格式（默认 YYYYMMDD）
        
        Returns:
            str: 格式化后的字符串，失败返回 None
        
        Examples:
            to_format(datetime(2024, 1, 15)) -> "20240115"
            to_format(date(2024, 1, 15), FMT_YYYY_MM_DD) -> "2024-01-15"
            to_format("20240115", FMT_YYYY_MM_DD) -> "2024-01-15"
        """
        if fmt is None:
            fmt = DateUtils.DEFAULT_FORMAT
        return date_parser.to_format_impl(input, fmt)
    
    @staticmethod
    def normalize(input: Any, fmt: str = None) -> Optional[str]:
        """
        通用标准化：将任意输入标准化为指定格式（智能识别）
        
        Args:
            input: 可以是 datetime, date, str, YYYYMM, YYYYQ1 等
            fmt: 目标格式（默认 YYYYMMDD）
        
        Returns:
            str: 标准化后的字符串，失败返回 None
        
        Examples:
            normalize("2024-01-15") -> "20240115"
            normalize(datetime(2024, 1, 15)) -> "20240115"
            normalize("202401") -> "20240101" (视为当月第一天)
            normalize("2024Q1") -> "20240101" (视为季度第一天)
        """
        if fmt is None:
            fmt = DateUtils.DEFAULT_FORMAT
        return date_parser.normalize_impl(input, fmt)
    
    # ==================== 格式转换（特定方向方法）====================
    
    @staticmethod
    def datetime_to_format(dt: datetime, fmt: str = None) -> str:
        """
        明确：datetime → str
        
        Raises:
            ValueError: 如果输入不是 datetime
        """
        if fmt is None:
            fmt = DateUtils.DEFAULT_FORMAT
        return date_parser.datetime_to_format_impl(dt, fmt)
    
    @staticmethod
    def date_to_format(d: date, fmt: str = None) -> str:
        """
        明确：date → str
        
        Raises:
            ValueError: 如果输入不是 date
        """
        if fmt is None:
            fmt = DateUtils.DEFAULT_FORMAT
        return date_parser.date_to_format_impl(d, fmt)
    
    @staticmethod
    def str_to_format(date_str: str, to_fmt: str, from_fmt: Optional[str] = None) -> Optional[str]:
        """
        明确：str → str（格式转换）
        
        Args:
            date_str: 源日期字符串
            to_fmt: 目标格式
            from_fmt: 源格式（None 时自动识别）
        
        Returns:
            str: 转换后的字符串，失败返回 None
        """
        return date_parser.str_to_format_impl(date_str, to_fmt, from_fmt)
    
    @staticmethod
    def normalize_datetime(dt: datetime, fmt: str = None) -> str:
        """明确：datetime → str（标准化）"""
        if fmt is None:
            fmt = DateUtils.DEFAULT_FORMAT
        return date_parser.normalize_datetime_impl(dt, fmt)
    
    @staticmethod
    def normalize_date(d: date, fmt: str = None) -> str:
        """明确：date → str（标准化）"""
        if fmt is None:
            fmt = DateUtils.DEFAULT_FORMAT
        return date_parser.normalize_date_impl(d, fmt)
    
    @staticmethod
    def normalize_str(date_str: str, fmt: str = None) -> Optional[str]:
        """
        明确：str → str（标准化）
        
        支持自动识别：YYYYMMDD, YYYY-MM-DD, YYYYMM, YYYYQ1 等
        """
        if fmt is None:
            fmt = DateUtils.DEFAULT_FORMAT
        return date_parser.normalize_str_impl(date_str, fmt)
    
    @staticmethod
    def str_to_datetime(date_str: str, fmt: Optional[str] = None) -> datetime:
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
        return date_parser.str_to_datetime_impl(date_str, fmt)
    
    # ==================== 日期 ↔ 周期转换 ====================
    
    @staticmethod
    def to_period_str(date: str, period_type: str) -> str:
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
        return date_period.to_period_str_impl(date, period_type)
    
    @staticmethod
    def from_period_str(period_str: str, period_type: str, is_start: bool = True) -> str:
        """
        将周期字符串转换为日期
        
        Args:
            period_str: 周期字符串
            period_type: PERIOD_DAY/MONTH/QUARTER/YEAR
            is_start: True=起始日，False=结束日
        
        Returns:
            str: YYYYMMDD 格式
        """
        return date_period.from_period_str_impl(period_str, period_type, is_start)
    
    # ==================== 日期计算 ====================
    
    @staticmethod
    def today() -> str:
        """获取今天，返回 YYYYMMDD"""
        return date_calculator.today_impl()
    
    @staticmethod
    def add_days(date: str, days: int) -> str:
        """加 N 天"""
        return date_calculator.add_days_impl(date, days)
    
    @staticmethod
    def sub_days(date: str, days: int) -> str:
        """减 N 天"""
        return date_calculator.sub_days_impl(date, days)
    
    @staticmethod
    def diff_days(date1: str, date2: str) -> int:
        """计算天数差（date2 - date1）"""
        return date_calculator.diff_days_impl(date1, date2)
    
    @staticmethod
    def get_month_start(date: str) -> str:
        """获取月初"""
        return date_calculator.get_month_start_impl(date)
    
    @staticmethod
    def get_month_end(date: str) -> str:
        """获取月末"""
        return date_calculator.get_month_end_impl(date)
    
    @staticmethod
    def get_quarter_start(date: str) -> str:
        """获取季度初"""
        return date_calculator.get_quarter_start_impl(date)
    
    @staticmethod
    def get_quarter_end(date: str) -> str:
        """获取季度末"""
        return date_calculator.get_quarter_end_impl(date)
    
    @staticmethod
    def get_week_start(date: str) -> str:
        """获取周一"""
        return date_calculator.get_week_start_impl(date)
    
    @staticmethod
    def get_week_end(date: str) -> str:
        """获取周日"""
        return date_calculator.get_week_end_impl(date)
    
    @staticmethod
    def get_period_end(date: str, term: str) -> Optional[str]:
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
        
        Example:
            >>> DateUtils.get_period_end("20260115", "weekly")
            "20260121"  # 20260115所在周的周日
            >>> DateUtils.get_period_end("20260115", "monthly")
            "20260131"  # 20260115所在月的最后一天
            >>> DateUtils.get_period_end("20260215", "quarterly")
            "20260331"  # 20260215所在季度（Q1）的最后一天
        """
        return date_calculator.get_period_end_impl(date, term)
    
    @staticmethod
    def get_previous_period_end(current_date: str, term: str) -> Optional[str]:
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
        
        Example:
            >>> DateUtils.get_previous_period_end("20260202", "weekly")  # 20260202是周一
            "20260201"  # 上一周的周日
            >>> DateUtils.get_previous_period_end("20260202", "monthly")  # 20260202是2月2日
            "20260131"  # 上一月的最后一天
            >>> DateUtils.get_previous_period_end("20260415", "quarterly")  # 20260415是Q2
            "20260331"  # 上一季度（Q1）的最后一天
        """
        return date_calculator.get_previous_period_end_impl(current_date, term)
    
    @staticmethod
    def is_before(date1: str, date2: str) -> bool:
        """date1 是否在 date2 之前"""
        return date_calculator.is_before_impl(date1, date2)
    
    @staticmethod
    def is_after(date1: str, date2: str) -> bool:
        """date1 是否在 date2 之后"""
        return date_calculator.is_after_impl(date1, date2)
    
    @staticmethod
    def is_same(date1: str, date2: str) -> bool:
        """是否同一天"""
        return date_calculator.is_same_impl(date1, date2)
    
    @staticmethod
    def is_today(date_str: str) -> bool:
        """判断日期是否为今天"""
        normalized = DateUtils.normalize_str(date_str)
        if not normalized:
            return False
        return normalized == DateUtils.today()
    
    @staticmethod
    def get_previous_week_end(date: str) -> str:
        """获取指定日期所在周的前一周周日"""
        week_start = DateUtils.get_week_start(date)
        previous_sunday = DateUtils.sub_days(week_start, 1)
        return previous_sunday
    
    @staticmethod
    def get_previous_month_end(date: str) -> str:
        """获取指定日期所在月的前一个月最后一天"""
        month_start = DateUtils.get_month_start(date)
        previous_month_end = DateUtils.sub_days(month_start, 1)
        return previous_month_end
    
    # ==================== 周期计算（核心功能）====================
    
    @staticmethod
    def add_periods(period: str, count: int, period_type: str) -> str:
        """
        周期加法
        
        Examples:
            add_periods("202401", 3, PERIOD_MONTH) -> "202404"
            add_periods("2024Q1", 2, PERIOD_QUARTER) -> "2024Q3"
        """
        return date_period.add_periods_impl(period, count, period_type)
    
    @staticmethod
    def sub_periods(period: str, count: int, period_type: str) -> str:
        """周期减法"""
        return date_period.sub_periods_impl(period, count, period_type)
    
    @staticmethod
    def diff_periods(period1: str, period2: str, period_type: str) -> int:
        """
        计算周期差值
        
        Returns:
            int: period2 - period1 的周期数
        """
        return date_period.diff_periods_impl(period1, period2, period_type)
    
    @staticmethod
    def is_period_before(period1: str, period2: str, period_type: str) -> bool:
        """period1 是否在 period2 之前"""
        return date_period.is_period_before_impl(period1, period2, period_type)
    
    @staticmethod
    def is_period_after(period1: str, period2: str, period_type: str) -> bool:
        """period1 是否在 period2 之后"""
        return date_period.is_period_after_impl(period1, period2, period_type)
    
    @staticmethod
    def generate_period_range(start: str, end: str, period_type: str) -> List[str]:
        """
        生成周期序列
        
        Examples:
            generate_period_range("202401", "202404", PERIOD_MONTH)
            -> ["202401", "202402", "202403", "202404"]
        """
        return date_period.generate_period_range_impl(start, end, period_type)
    
    @staticmethod
    def normalize_period_type(period_type: str) -> str:
        """
        规范化周期类型字符串
        
        Examples:
            "daily" -> "day"
            "monthly" -> "month"
            "quarterly" -> "quarter"
        """
        return date_period.normalize_period_type(period_type)
    
    @staticmethod
    def detect_period_type(period_str: str) -> str:
        """
        自动识别周期字符串类型
        
        Examples:
            "202401" -> "month"
            "2024Q1" -> "quarter"
        """
        return date_period.detect_period_type(period_str)
    
    @staticmethod
    def get_period_sort_key(period_str: str, period_type: str) -> str:
        """
        获取排序键（用于排序）
        
        将周期字符串转换为日期作为排序键
        """
        return date_period.get_period_sort_key_impl(period_str, period_type)
    
    @staticmethod
    def normalize_period_value(value: Any, period: str) -> Optional[str]:
        """
        将任意输入标准化为指定周期的字符串表示
        
        Args:
            value: 可以是 datetime, date, str（自动识别）
            period: PERIOD_DAY/MONTH/QUARTER/YEAR
        
        Returns:
            str: 标准化后的周期字符串
            - PERIOD_DAY -> "20240115"
            - PERIOD_MONTH -> "202401"
            - PERIOD_QUARTER -> "2024Q1"
            - PERIOD_YEAR -> "2024"
            失败返回 None
        """
        # 先标准化为日期字符串
        date_str = DateUtils.normalize(value)
        if not date_str:
            return None
        
        # 转换为周期字符串
        try:
            return DateUtils.to_period_str(date_str, period)
        except Exception:
            return None
    
    # ==================== 季度专用（便捷方法）====================
    
    @staticmethod
    def date_to_quarter(date: str) -> str:
        """YYYYMMDD -> 2024Q1"""
        return date_parser.date_to_quarter_str(date)
    
    @staticmethod
    def quarter_to_date(quarter: str, is_start: bool = True) -> str:
        """
        2024Q1 -> YYYYMMDD
        
        Args:
            is_start: True=季度第一天，False=季度最后一天
        """
        result = date_parser.quarter_to_date_str(quarter, is_start)
        if not result:
            raise ValueError(f"季度格式错误: {quarter}，应为 YYYYQ1")
        return result
    
    @staticmethod
    def add_quarters(quarter: str, count: int) -> str:
        """季度加法（便捷方法）"""
        return date_period.add_quarters_impl(quarter, count)
    
    @staticmethod
    def sub_quarters(quarter: str, count: int) -> str:
        """季度减法（便捷方法）"""
        return date_period.sub_quarters_impl(quarter, count)
    
    @staticmethod
    def diff_quarters(quarter1: str, quarter2: str) -> int:
        """季度差值（便捷方法）"""
        return date_period.diff_quarters_impl(quarter1, quarter2)
    
    @staticmethod
    def get_current_quarter(date: str) -> str:
        """获取指定日期所在的季度（YYYYQ1格式）"""
        return DateUtils.date_to_quarter(date)
    
    @staticmethod
    def get_next_quarter(quarter: str) -> str:
        """获取下一个季度（便捷方法）"""
        return DateUtils.add_quarters(quarter, 1)
    
    @staticmethod
    def get_quarter_start_date(quarter: str) -> str:
        """获取季度起始日期（便捷方法）"""
        return DateUtils.quarter_to_date(quarter, is_start=True)
