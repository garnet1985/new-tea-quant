#!/usr/bin/env python3
"""
日期工具类 - 提供统一的日期转换和处理方法
"""
from datetime import datetime, timedelta
from typing import List, Optional
from enum import Enum


class DateFormat(Enum):
    """
    日期格式枚举 - 定义系统内使用的所有标准日期格式
    
    用于日期标准化输出格式，支持以下格式：
    - DAY: YYYYMMDD 格式（如 "20240101"）
    - MONTH: YYYYMM 格式（如 "202401"）
    - QUARTER: YYYYQ[1-4] 格式（如 "2024Q1"）
    - NONE: 不进行标准化
    """
    DAY = "day"  # YYYYMMDD 格式，如 "20240101"
    MONTH = "month"  # YYYYMM 格式，如 "202401"
    QUARTER = "quarter"  # YYYYQ[1-4] 格式，如 "2024Q1"
    NONE = "none"  # 不进行标准化


class DateUtils:
    """日期工具类 - 提供静态方法处理各种日期转换"""
    
    # 常用日期格式
    DATE_FORMAT_YYYYMMDD = '%Y%m%d'
    DATE_FORMAT_YYYY_MM_DD = '%Y-%m-%d'
    DATE_FORMAT_YYYY_MM_DD_HH_MM_SS = '%Y-%m-%d %H:%M:%S'
    
    # 默认日期常量
    DEFAULT_START_DATE = '20080101'
    DEFAULT_END_DATE = '20251231'
    
    @staticmethod
    def get_current_date_str(format_str: str = DATE_FORMAT_YYYYMMDD) -> str:
        """
        获取当前日期字符串
        
        Args:
            format_str: 日期格式
            
        Returns:
            str: 当前日期字符串
        """
        return datetime.now().strftime(format_str)
    
    @staticmethod
    def is_before_or_same_day(date1: str, date2: str) -> bool:
        """
        判断date1是否在date2之前或同一天
        """
        date1_obj = datetime.strptime(date1, DateUtils.DATE_FORMAT_YYYYMMDD)
        date2_obj = datetime.strptime(date2, DateUtils.DATE_FORMAT_YYYYMMDD)
        return date1_obj.date() <= date2_obj.date()

    @staticmethod
    def convert_date_format(date_str: str, from_format: str, to_format: str) -> str:
        """
        转换日期格式
        
        Args:
            date_str: 原始日期字符串
            from_format: 原始格式
            to_format: 目标格式
            
        Returns:
            str: 转换后的日期字符串
        """
        try:
            date_obj = datetime.strptime(date_str, from_format)
            return date_obj.strftime(to_format)
        except ValueError as e:
            raise ValueError(f"日期格式转换失败: {date_str} from {from_format} to {to_format}, error: {e}")
    
    @staticmethod
    def yyyymmdd_to_yyyy_mm_dd(date_str: str) -> str:
        """
        YYYYMMDD 格式转换为 YYYY-MM-DD 格式
        
        Args:
            date_str: YYYYMMDD 格式的日期字符串
            
        Returns:
            str: YYYY-MM-DD 格式的日期字符串
        """
        return DateUtils.convert_date_format(date_str, DateUtils.DATE_FORMAT_YYYYMMDD, DateUtils.DATE_FORMAT_YYYY_MM_DD)
    
    @staticmethod
    def yyyy_mm_dd_to_yyyymmdd(date_str: str) -> str:
        """
        YYYY-MM-DD 格式转换为 YYYYMMDD 格式
        
        Args:
            date_str: YYYY-MM-DD 格式的日期字符串
            
        Returns:
            str: YYYYMMDD 格式的日期字符串
        """
        return DateUtils.convert_date_format(date_str, DateUtils.DATE_FORMAT_YYYY_MM_DD, DateUtils.DATE_FORMAT_YYYYMMDD)
    
    @staticmethod
    def generate_date_range(start_date: str, end_date: str, 
                          start_format: str = DATE_FORMAT_YYYYMMDD,
                          end_format: str = DATE_FORMAT_YYYYMMDD,
                          output_format: str = DATE_FORMAT_YYYY_MM_DD) -> List[str]:
        """
        生成日期范围列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            start_format: 开始日期格式
            end_format: 结束日期格式
            output_format: 输出格式
            
        Returns:
            List[str]: 日期字符串列表
        """
        try:
            start_dt = datetime.strptime(start_date, start_format)
            end_dt = datetime.strptime(end_date, end_format)
            
            date_list = []
            current_dt = start_dt
            while current_dt <= end_dt:
                date_list.append(current_dt.strftime(output_format))
                current_dt += timedelta(days=1)
            
            return date_list
            
        except ValueError as e:
            raise ValueError(f"生成日期范围失败: {start_date} to {end_date}, error: {e}")
    
    @staticmethod
    def get_date_before_days(date_str: str, days: int, 
                           input_format: str = DATE_FORMAT_YYYYMMDD,
                           output_format: str = DATE_FORMAT_YYYYMMDD) -> str:
        """
        获取指定天数前的日期
        
        Args:
            date_str: 基准日期
            days: 天数
            input_format: 输入格式
            output_format: 输出格式
            
        Returns:
            str: 计算后的日期字符串
        """
        try:
            date_obj = datetime.strptime(date_str, input_format)
            result_date = date_obj - timedelta(days=days)
            return result_date.strftime(output_format)
        except ValueError as e:
            raise ValueError(f"计算日期失败: {date_str}, error: {e}")
    
    @staticmethod
    def get_date_after_days(date_str: str, days: int, 
                          input_format: str = DATE_FORMAT_YYYYMMDD,
                          output_format: str = DATE_FORMAT_YYYYMMDD) -> str:
        """
        获取指定天数后的日期
        
        Args:
            date_str: 基准日期
            days: 天数
            input_format: 输入格式
            output_format: 输出格式
            
        Returns:
            str: 计算后的日期字符串
        """
        try:
            date_obj = datetime.strptime(date_str, input_format)
            result_date = date_obj + timedelta(days=days)
            return result_date.strftime(output_format)
        except ValueError as e:
            raise ValueError(f"计算日期失败: {date_str}, error: {e}")
    
    @staticmethod
    def get_duration_by_term(term: str, start_date: str, end_date: str) -> int:
        """
        计算两个日期之间的term单位差
        """
        if term == 'daily':
            return DateUtils.get_duration_in_days(start_date, end_date)
        elif term == 'weekly':
            return DateUtils.get_duration_in_days(start_date, end_date) // 7
        elif term == 'monthly':
            return DateUtils.get_duration_in_days(start_date, end_date) // 30


    @staticmethod
    def get_duration_in_days(start_date: str, end_date: str, 
                           date_format: str = DATE_FORMAT_YYYYMMDD) -> int:
        """
        计算两个日期之间的天数差
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            date_format: 日期格式
            
        Returns:
            int: 天数差
        """
        try:
            start_obj = datetime.strptime(start_date, date_format)
            end_obj = datetime.strptime(end_date, date_format)
            delta = end_obj - start_obj
            return delta.days
        except ValueError as e:
            raise ValueError(f"计算日期差失败: {start_date} to {end_date}, error: {e}")
    
    @staticmethod
    def parse_yyyymmdd(date_str: str) -> datetime:
        """
        解析 YYYYMMDD 格式的日期字符串
        
        Args:
            date_str: YYYYMMDD 格式的日期字符串
            
        Returns:
            datetime: 日期对象
        """
        return datetime.strptime(date_str, DateUtils.DATE_FORMAT_YYYYMMDD)
    
    @staticmethod
    def format_to_yyyymmdd(date_obj: datetime) -> str:
        """
        将日期对象格式化为 YYYYMMDD 字符串
        
        Args:
            date_obj: 日期对象
        
        Returns:
            str: YYYYMMDD 格式的日期字符串
        """
        return date_obj.strftime(DateUtils.DATE_FORMAT_YYYYMMDD)
    
    @staticmethod
    def normalize_date(date_str: str) -> Optional[str]:
        """
        将各种日期格式标准化为 YYYYMMDD 格式
        
        支持的输入格式：
        - YYYYMMDD (如 "20240101")
        - YYYY-MM-DD (如 "2024-01-01")
        
        Args:
            date_str: 日期字符串
        
        Returns:
            str: YYYYMMDD 格式的日期字符串，如果无法解析返回 None
        """
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # 如果已经是 YYYYMMDD 格式
        if len(date_str) == 8 and date_str.isdigit():
            return date_str
        
        # 如果是 YYYY-MM-DD 格式
        if len(date_str) == 10 and date_str.count('-') == 2:
            try:
                return DateUtils.yyyy_mm_dd_to_yyyymmdd(date_str)
            except ValueError:
                return None
        
        # 尝试其他格式
        try:
            # 尝试解析为常见格式
            for fmt in [DateUtils.DATE_FORMAT_YYYY_MM_DD, DateUtils.DATE_FORMAT_YYYYMMDD]:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime(DateUtils.DATE_FORMAT_YYYYMMDD)
                except ValueError:
                    continue
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def normalize_to_format(date_value: any, output_format: DateFormat) -> Optional[str]:
        """
        将任何时间形式标准化为系统内使用的标准时间格式。
        
        支持的输入格式：
        - YYYYMMDD (如 "20240101")
        - YYYY-MM-DD (如 "2024-01-01")
        - YYYYMM (如 "202401")
        - YYYY-MM (如 "2024-01")
        - YYYYQ[1-4] (如 "2024Q1")
        - datetime/date 对象
        - 其他常见日期格式
        
        Args:
            date_value: 日期值（字符串、datetime对象等）
            output_format: 输出格式枚举（DateFormat.DAY, DateFormat.MONTH, DateFormat.QUARTER）
            
        Returns:
            str: 标准化后的日期字符串，格式取决于 output_format：
                - DateFormat.DAY: YYYYMMDD (如 "20240101")
                - DateFormat.MONTH: YYYYMM (如 "202401")
                - DateFormat.QUARTER: YYYYQ[1-4] (如 "2024Q1")
           如果无法解析或 output_format 为 DateFormat.NONE，返回 None
        """
        if output_format == DateFormat.NONE:
            return None
        
        if date_value is None:
            return None
        
        # 如果是 datetime/date 对象，先转换为字符串
        if isinstance(date_value, (datetime,)):
            date_value = date_value.strftime(DateUtils.DATE_FORMAT_YYYYMMDD)
        elif hasattr(date_value, 'date'):  # date 对象
            date_value = date_value.strftime(DateUtils.DATE_FORMAT_YYYYMMDD)
        
        date_str = str(date_value).strip()
        if not date_str:
            return None
        
        # 先标准化为 YYYYMMDD 格式（中间格式）
        yyyymmdd = DateUtils.normalize_date(date_str)
        if not yyyymmdd:
            # 如果 normalize_date 失败，尝试其他解析方式
            # 尝试解析为月份格式 YYYYMM
            month_clean = ''.join(c for c in date_str if c.isdigit())
            if len(month_clean) == 6:
                # 可能是 YYYYMM 格式，补充日期为当月第一天
                try:
                    yyyymmdd = f"{month_clean}01"
                    # 验证日期是否有效
                    datetime.strptime(yyyymmdd, DateUtils.DATE_FORMAT_YYYYMMDD)
                except ValueError:
                    return None
            elif len(month_clean) == 8:
                # 可能是 YYYYMMDD 格式，但 normalize_date 没识别到
                try:
                    datetime.strptime(month_clean, DateUtils.DATE_FORMAT_YYYYMMDD)
                    yyyymmdd = month_clean
                except ValueError:
                    return None
            else:
                return None
        
        # 根据输出格式转换
        if output_format == DateFormat.DAY:
            return yyyymmdd
        elif output_format == DateFormat.MONTH:
            return yyyymmdd[:6]  # YYYYMM
        elif output_format == DateFormat.QUARTER:
            return DateUtils.date_to_quarter(yyyymmdd)
        else:
            return None
    
    @staticmethod
    def date_to_quarter(date_str: str) -> str:
        """
        将日期（YYYYMMDD）转换为季度（YYYYQ[1-4]）
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
        
        Returns:
            str: 季度字符串（YYYYQ[1-4]）
        """
        if not date_str or len(date_str) != 8:
            raise ValueError(f"日期格式错误: {date_str}，应为 YYYYMMDD 格式")
        
        year = int(date_str[:4])
        month = int(date_str[4:6])
        
        if month <= 3:
            quarter = 1
        elif month <= 6:
            quarter = 2
        elif month <= 9:
            quarter = 3
        else:
            quarter = 4
        
        return f"{year}Q{quarter}"
    
    @staticmethod
    def quarter_to_date(quarter_str: str, is_start: bool = True) -> str:
        """
        将季度（YYYYQ[1-4]）转换为日期（YYYYMMDD）
        
        Args:
            quarter_str: 季度字符串（YYYYQ[1-4]）
            is_start: True 返回季度开始日期，False 返回季度结束日期
        
        Returns:
            str: 日期字符串（YYYYMMDD）
        """
        if not quarter_str or len(quarter_str) != 6 or quarter_str[4] != 'Q':
            raise ValueError(f"季度格式错误: {quarter_str}，应为 YYYYQ[1-4] 格式")
        
        year = int(quarter_str[:4])
        quarter = int(quarter_str[5])
        
        if quarter < 1 or quarter > 4:
            raise ValueError(f"季度值错误: {quarter}，应为 1-4")
        
        if is_start:
            # 季度开始日期
            if quarter == 1:
                return f"{year}0101"
            elif quarter == 2:
                return f"{year}0401"
            elif quarter == 3:
                return f"{year}0701"
            else:  # quarter == 4
                return f"{year}1001"
        else:
            # 季度结束日期
            if quarter == 1:
                return f"{year}0331"
            elif quarter == 2:
                return f"{year}0630"
            elif quarter == 3:
                return f"{year}0930"
            else:  # quarter == 4
                return f"{year}1231"
    
    @staticmethod
    def get_current_quarter(date_str: str = None) -> str:
        """
        根据日期获取当前季度
        
        Args:
            date_str: 日期字符串（YYYYMMDD格式），如果为 None 则使用当前日期
        
        Returns:
            str: 季度字符串（YYYYQ[1-4]）
        """
        if date_str is None:
            date_str = DateUtils.get_current_date_str()
        return DateUtils.date_to_quarter(date_str)
    
    @staticmethod
    def get_start_date_of_quarter(quarter_str: str) -> str:
        """
        获取季度的开始日期
        
        Args:
            quarter_str: 季度字符串（YYYYQ[1-4]格式）
        
        Returns:
            str: 季度开始日期（YYYYMMDD格式）
        """
        return DateUtils.quarter_to_date(quarter_str, is_start=True)
    
    @staticmethod
    def get_end_date_of_quarter(quarter_str: str) -> str:
        """
        获取季度的结束日期
        
        Args:
            quarter_str: 季度字符串（YYYYQ[1-4]格式）
        
        Returns:
            str: 季度结束日期（YYYYMMDD格式）
        """
        return DateUtils.quarter_to_date(quarter_str, is_start=False)

    @staticmethod
    def get_previous_quarter(quarter_str: str) -> str:
        """
        获取上一个季度
        
        Args:
            quarter_str: 季度字符串（YYYYQ[1-4]格式）
        
        Returns:
            str: 上一个季度（YYYYQ[1-4]格式）
        """
        year = int(quarter_str[:4])
        quarter = int(quarter_str[5])
        
        if quarter > 1:
            return f"{year}Q{quarter - 1}"
        else:
            return f"{year - 1}Q4"

    @staticmethod
    def get_next_quarter(quarter_str: str) -> str:
        """
        获取下一个季度
        
        Args:
            quarter_str: 季度字符串（YYYYQ[1-4]格式）
        
        Returns:
            str: 下一个季度（YYYYQ[1-4]格式）
        """
        year = int(quarter_str[:4])
        quarter = int(quarter_str[5])
        
        if quarter < 4:
            return f"{year}Q{quarter + 1}"
        else:
            return f"{year + 1}Q1"
    
    @staticmethod
    def get_previous_day(date_str: str) -> str:
        """
        获取前一天的日期（自然日）
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
        
        Returns:
            str: 前一天的日期，格式YYYYMMDD
        """
        return DateUtils.get_date_before_days(date_str, 1)
    
    @staticmethod
    def get_next_date(date_str: str) -> str:
        """
        获取下一天的日期（自然日）
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
        
        Returns:
            str: 下一天的日期，格式YYYYMMDD
        """
        return DateUtils.get_date_after_days(date_str, 1)
    
    @staticmethod
    def get_date_before_with_multiplier(date_str: str, days: int, multiplier: float = 1.0) -> str:
        """
        获取 N 天前的日期（支持倍数，用于交易日估算）
        
        例如：如果需要 30 个交易日的数据，可以使用 multiplier=1.5 来估算自然日
        days=30, multiplier=1.5 → 实际计算 45 天前，确保有足够的交易日数据
        
        Args:
            date_str: 基准日期（YYYYMMDD）
            days: 天数
            multiplier: 倍数（默认 1.0，即自然日）
        
        Returns:
            str: N 天前的日期（YYYYMMDD）
        """
        actual_days = int(days * multiplier)
        return DateUtils.get_date_before_days(date_str, actual_days)
    
    @staticmethod
    def get_previous_week_end(date_str: str) -> str:
        """
        获取指定日期所在周的前一周的周日
        
        逻辑：
        1. 找到date所在周的周一
        2. 前一周的周日 = 本周周一 - 1天
        
        例如：
        - 20250930 (周二) → 本周一=20250929 → 前一周日=20250928
        - 20251006 (周一) → 本周一=20251006 → 前一周日=20251005
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
            
        Returns:
            str: 前一周的周日，格式YYYYMMDD
        """
        date_obj = DateUtils.parse_yyyymmdd(date_str)
        
        # 计算本周的周一
        days_since_monday = date_obj.weekday()  # 周一=0, 周日=6
        this_week_monday = date_obj - timedelta(days=days_since_monday)
        
        # 前一周的周日 = 本周周一 - 1天
        last_week_sunday = this_week_monday - timedelta(days=1)
        
        return last_week_sunday.strftime(DateUtils.DATE_FORMAT_YYYYMMDD)
    
    @staticmethod
    def get_previous_month_end(date_str: str) -> str:
        """
        获取指定日期所在月的前一个月的最后一天
        
        逻辑：
        1. 找到date所在月
        2. 计算前一个月的最后一天
        
        例如：
        - 20250930 → 所在月=9月 → 前一月=8月 → 返回 20250831
        - 20251105 → 所在月=11月 → 前一月=10月 → 返回 20251031
        - 20250115 → 所在月=1月 → 前一月=12月 → 返回 20241231
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
            
        Returns:
            str: 前一个月的最后一天，格式YYYYMMDD
        """
        import calendar
        
        year = int(date_str[:4])
        month = int(date_str[4:6])
        
        # 前一个月的年月
        if month == 1:
            last_month_year = year - 1
            last_month = 12
        else:
            last_month_year = year
            last_month = month - 1
        
        # 前一个月的最后一天
        last_day = calendar.monthrange(last_month_year, last_month)[1]
        
        return f"{last_month_year}{last_month:02d}{last_day:02d}"
    
    # ========== 周期格式处理（quarter/month/day）==========

    @staticmethod
    def _normalize_date_format(date_format: str) -> str:
        """将 TermType 值（daily/monthly/quarterly）规范为内部格式（day/month/quarter）。"""
        if not date_format:
            return "day"
        v = (date_format or "").lower()
        if v in ("daily", "day", "date"):
            return "day"
        if v in ("monthly", "month"):
            return "month"
        if v in ("quarterly", "quarter"):
            return "quarter"
        return v
    
    @staticmethod
    def get_current_period(current_date: str, date_format: str):
        """
        根据 date_format 获取当前周期值
        
        将 YYYYMMDD 格式的日期转换为对应的周期格式。
        
        Args:
            current_date: 日期字符串（YYYYMMDD）
            date_format: 日期格式（"quarter" | "month" | "day"）
        
        Returns:
            - quarter: (year, quarter) 元组，如 (2024, 1)
            - month: (year, month) 元组，如 (2024, 1)
            - day: 日期字符串（YYYYMMDD）
        
        Example:
            >>> DateUtils.get_current_period("20240315", "quarter")
            (2024, 1)
            >>> DateUtils.get_current_period("20240315", "month")
            (2024, 3)
            >>> DateUtils.get_current_period("20240315", "day")
            "20240315"
        """
        date_format = DateUtils._normalize_date_format(date_format)
        if date_format == "quarter":
            current_year = int(current_date[:4])
            current_month = int(current_date[4:6])
            if current_month <= 3:
                return (current_year, 1)
            elif current_month <= 6:
                return (current_year, 2)
            elif current_month <= 9:
                return (current_year, 3)
            else:
                return (current_year, 4)
        elif date_format == "month":
            return (int(current_date[:4]), int(current_date[4:6]))
        else:  # date_format == "day" or "date"
            return current_date
    
    @staticmethod
    def parse_period(value: str, date_format: str):
        """
        解析周期格式字符串
        
        Args:
            value: 周期字符串
                - quarter: "2024Q1" 格式
                - month: "202403" 格式
                - day: "20240315" 格式
            date_format: 日期格式（"quarter" | "month" | "day"）
        
        Returns:
            - quarter: (year, quarter) 元组
            - month: (year, month) 元组
            - day: 日期字符串（YYYYMMDD）
        
        Example:
            >>> DateUtils.parse_period("2024Q1", "quarter")
            (2024, 1)
            >>> DateUtils.parse_period("202403", "month")
            (2024, 3)
            >>> DateUtils.parse_period("20240315", "day")
            "20240315"
        """
        date_format = DateUtils._normalize_date_format(date_format)
        if date_format == "quarter":
            year = int(value[:4])
            quarter = int(value[5])
            return (year, quarter)
        elif date_format == "month":
            return (int(value[:4]), int(value[4:6]))
        else:  # date_format == "day" or "date"
            return value
    
    @staticmethod
    def format_period(value, date_format: str) -> str:
        """
        格式化周期值为字符串
        
        Args:
            value: 周期值
                - quarter: (year, quarter) 元组
                - month: (year, month) 元组
                - day: 日期字符串（YYYYMMDD）
            date_format: 日期格式（"quarter" | "month" | "day"）
        
        Returns:
            格式化后的字符串
                - quarter: "2024Q1"
                - month: "202403"
                - day: "20240315"
        
        Example:
            >>> DateUtils.format_period((2024, 1), "quarter")
            "2024Q1"
            >>> DateUtils.format_period((2024, 3), "month")
            "202403"
            >>> DateUtils.format_period("20240315", "day")
            "20240315"
        """
        date_format = DateUtils._normalize_date_format(date_format)
        if date_format == "quarter":
            year, quarter = value
            return f"{year}Q{quarter}"
        elif date_format == "month":
            year, month = value
            return f"{year}{month:02d}"
        else:  # date_format == "day" or "date"
            return value
    
    @staticmethod
    def calculate_period_diff(latest_value: str, current_value, date_format: str) -> int:
        """
        计算两个日期之间的周期差
        
        Args:
            latest_value: 最新周期字符串
            current_value: 当前周期值（元组或字符串）
            date_format: 日期格式（"quarter" | "month" | "day"）
        
        Returns:
            周期差（整数）
                - quarter: 季度差
                - month: 月份差
                - day: 天数差
        
        Example:
            >>> DateUtils.calculate_period_diff("2023Q4", (2024, 2), "quarter")
            2
            >>> DateUtils.calculate_period_diff("202401", (2024, 3), "month")
            2
        """
        date_format = DateUtils._normalize_date_format(date_format)
        latest = DateUtils.parse_period(latest_value, date_format)
        current = current_value
        
        if date_format == "quarter":
            latest_year, latest_quarter = latest
            current_year, current_quarter = current
            return (current_year - latest_year) * 4 + (current_quarter - latest_quarter)
        elif date_format == "month":
            latest_year, latest_month = latest
            current_year, current_month = current
            return (current_year - latest_year) * 12 + (current_month - latest_month)
        else:  # date_format == "day" or "date"
            latest_date = DateUtils.parse_yyyymmdd(latest)
            current_date = DateUtils.parse_yyyymmdd(current)
            return (current_date - latest_date).days
    
    @staticmethod
    def subtract_periods(value, periods: int, date_format: str):
        """
        减去 N 个周期
        
        Args:
            value: 周期值（元组或字符串）
            periods: 要减去的周期数
            date_format: 日期格式（"quarter" | "month" | "day"）
        
        Returns:
            减去周期后的值（元组或字符串）
        
        Example:
            >>> DateUtils.subtract_periods((2024, 2), 2, "quarter")
            (2023, 4)
            >>> DateUtils.subtract_periods((2024, 3), 5, "month")
            (2023, 10)
            >>> DateUtils.subtract_periods("20240315", 30, "day")
            "20240214"
        """
        from datetime import timedelta

        date_format = DateUtils._normalize_date_format(date_format)
        if date_format == "quarter":
            year, quarter = value
            quarter -= periods - 1
            while quarter < 1:
                quarter += 4
                year -= 1
            return (year, quarter)
        elif date_format == "month":
            year, month = value
            month -= periods - 1
            while month < 1:
                month += 12
                year -= 1
            return (year, month)
        else:  # date_format == "day" or "date"
            date = DateUtils.parse_yyyymmdd(value)
            new_date = date - timedelta(days=periods - 1)
            return DateUtils.format_to_yyyymmdd(new_date)
    
    @staticmethod
    def add_one_period(latest_value: str, date_format: str):
        """
        添加一个周期（用于历史追赶）
        
        Args:
            latest_value: 最新周期字符串
            date_format: 日期格式（"quarter" | "month" | "day"）
        
        Returns:
            添加一个周期后的值（元组或字符串）
        
        Example:
            >>> DateUtils.add_one_period("2023Q4", "quarter")
            (2024, 1)
            >>> DateUtils.add_one_period("202312", "month")
            (2024, 1)
            >>> DateUtils.add_one_period("20231231", "day")
            "20240101"
        """
        from datetime import timedelta

        date_format = DateUtils._normalize_date_format(date_format)
        latest = DateUtils.parse_period(latest_value, date_format)
        
        if date_format == "quarter":
            year, quarter = latest
            quarter += 1
            if quarter > 4:
                quarter = 1
                year += 1
            return (year, quarter)
        elif date_format == "month":
            year, month = latest
            month += 1
            if month > 12:
                month = 1
                year += 1
            return (year, month)
        else:  # date_format == "day" or "date"
            date = DateUtils.parse_yyyymmdd(latest)
            new_date = date + timedelta(days=1)
            return DateUtils.format_to_yyyymmdd(new_date)
    
    @staticmethod
    def get_period_unit(date_format: str) -> str:
        """
        获取周期单位名称
        
        Args:
            date_format: 日期格式（"quarter" | "month" | "day"）
        
        Returns:
            周期单位名称（"季度" | "个月" | "天"）
        
        Example:
            >>> DateUtils.get_period_unit("quarter")
            "季度"
            >>> DateUtils.get_period_unit("month")
            "个月"
            >>> DateUtils.get_period_unit("day")
            "天"
        """
        date_format = DateUtils._normalize_date_format(date_format)
        if date_format == "quarter":
            return "季度"
        elif date_format == "month":
            return "个月"
        else:  # date_format == "day" or "date"
            return "天"