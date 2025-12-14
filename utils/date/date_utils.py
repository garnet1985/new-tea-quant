#!/usr/bin/env python3
"""
日期工具类 - 提供统一的日期转换和处理方法
"""
from datetime import datetime, timedelta
from turtle import st
from typing import List, Optional


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