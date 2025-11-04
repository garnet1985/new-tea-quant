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
