"""
date_utils.py 单元测试
"""
try:
    import pytest
except ImportError:
    pytest = None

from datetime import datetime
from core.utils.date.date_utils import DateUtils


class TestDateUtils:
    """DateUtils 测试类"""
    
    def test_get_today_str(self):
        """测试获取当前日期字符串"""
        date_str = DateUtils.get_today_str()
        assert len(date_str) == 8
        assert date_str.isdigit()
        
        # 测试自定义格式
        date_str_custom = DateUtils.get_today_str(DateUtils.DATE_FORMAT_YYYY_MM_DD)
        assert len(date_str_custom) == 10
        assert '-' in date_str_custom
    
    def test_convert_date_format(self):
        """测试日期格式转换"""
        result = DateUtils.convert_date_format(
            "20240115",
            DateUtils.DATE_FORMAT_YYYYMMDD,
            DateUtils.DATE_FORMAT_YYYY_MM_DD
        )
        assert result == "2024-01-15"
    
    def test_yyyymmdd_to_yyyy_mm_dd(self):
        """测试 YYYYMMDD 转 YYYY-MM-DD"""
        result = DateUtils.yyyymmdd_to_yyyy_mm_dd("20240115")
        assert result == "2024-01-15"
    
    def test_yyyy_mm_dd_to_yyyymmdd(self):
        """测试 YYYY-MM-DD 转 YYYYMMDD"""
        result = DateUtils.yyyy_mm_dd_to_yyyymmdd("2024-01-15")
        assert result == "20240115"
    
    def test_generate_date_range(self):
        """测试生成日期范围"""
        dates = DateUtils.generate_date_range("20240101", "20240105")
        assert len(dates) == 5
        assert dates[0] == "2024-01-01"
        assert dates[4] == "2024-01-05"
    
    def test_get_date_before_days(self):
        """测试获取 N 天前的日期"""
        result = DateUtils.get_date_before_days("20240115", 5)
        assert result == "20240110"
    
    def test_get_date_after_days(self):
        """测试获取 N 天后的日期"""
        result = DateUtils.get_date_after_days("20240115", 5)
        assert result == "20240120"
    
    def test_get_next_date(self):
        """测试获取下一天"""
        result = DateUtils.get_next_date("20240115")
        assert result == "20240116"
    
    def test_get_previous_day(self):
        """测试获取前一天"""
        result = DateUtils.get_previous_day("20240115")
        assert result == "20240114"
    
    def test_get_date_before_with_multiplier(self):
        """测试获取 N 天前的日期（支持倍数）"""
        # 30 天 * 1.5 = 45 天
        result = DateUtils.get_date_before_with_multiplier("20240115", 30, multiplier=1.5)
        expected = DateUtils.get_date_before_days("20240115", 45)
        assert result == expected
    
    def test_get_duration_in_days(self):
        """测试计算天数差"""
        days = DateUtils.get_duration_in_days("20240101", "20240115")
        assert days == 14
    
    def test_get_duration_by_term(self):
        """测试按 term 计算时长"""
        days = DateUtils.get_duration_by_term("daily", "20240101", "20240115")
        assert days == 14
        
        weeks = DateUtils.get_duration_by_term("weekly", "20240101", "20240115")
        assert weeks == 2  # 14 天 // 7 = 2
        
        months = DateUtils.get_duration_by_term("monthly", "20240101", "20240115")
        assert months == 0  # 14 天 // 30 = 0
    
    def test_parse_yyyymmdd(self):
        """测试解析 YYYYMMDD"""
        date_obj = DateUtils.parse_yyyymmdd("20240115")
        assert isinstance(date_obj, datetime)
        assert date_obj.year == 2024
        assert date_obj.month == 1
        assert date_obj.day == 15
    
    def test_format_to_yyyymmdd(self):
        """测试格式化日期对象"""
        date_obj = datetime(2024, 1, 15)
        result = DateUtils.format_to_yyyymmdd(date_obj)
        assert result == "20240115"
    
    def test_normalize_date(self):
        """测试日期标准化"""
        # YYYYMMDD 格式
        assert DateUtils.normalize_date("20240115") == "20240115"
        
        # YYYY-MM-DD 格式
        assert DateUtils.normalize_date("2024-01-15") == "20240115"
        
        # None
        assert DateUtils.normalize_date(None) is None
        assert DateUtils.normalize_date("") is None
    
    def test_date_to_quarter(self):
        """测试日期转季度"""
        assert DateUtils.date_to_quarter("20240115") == "2024Q1"
        assert DateUtils.date_to_quarter("20240415") == "2024Q2"
        assert DateUtils.date_to_quarter("20240715") == "2024Q3"
        assert DateUtils.date_to_quarter("20241015") == "2024Q4"
    
    def test_quarter_to_date(self):
        """测试季度转日期"""
        # 季度开始
        assert DateUtils.quarter_to_date("2024Q1", is_start=True) == "20240101"
        assert DateUtils.quarter_to_date("2024Q2", is_start=True) == "20240401"
        
        # 季度结束
        assert DateUtils.quarter_to_date("2024Q1", is_start=False) == "20240331"
        assert DateUtils.quarter_to_date("2024Q2", is_start=False) == "20240630"
    
    def test_get_current_quarter(self):
        """测试获取当前季度"""
        quarter = DateUtils.get_current_quarter("20240115")
        assert quarter == "2024Q1"
    
    def test_get_start_date_of_quarter(self):
        """测试获取季度开始日期"""
        assert DateUtils.get_start_date_of_quarter("2024Q1") == "20240101"
    
    def test_get_end_date_of_quarter(self):
        """测试获取季度结束日期"""
        assert DateUtils.get_end_date_of_quarter("2024Q1") == "20240331"
    
    def test_get_previous_quarter(self):
        """测试获取上一个季度"""
        assert DateUtils.get_previous_quarter("2024Q2") == "2024Q1"
        assert DateUtils.get_previous_quarter("2024Q1") == "2023Q4"
    
    def test_get_next_quarter(self):
        """测试获取下一个季度"""
        assert DateUtils.get_next_quarter("2024Q1") == "2024Q2"
        assert DateUtils.get_next_quarter("2024Q4") == "2025Q1"
    
    def test_get_previous_week_end(self):
        """测试获取前一周的周日"""
        # 20250930 是周二，前一周的周日应该是 20250928
        result = DateUtils.get_previous_week_end("20250930")
        assert result == "20250928"
    
    def test_get_previous_month_end(self):
        """测试获取前一个月的最后一天"""
        assert DateUtils.get_previous_month_end("20250930") == "20250831"
        assert DateUtils.get_previous_month_end("20250115") == "20241231"
    
    def test_is_before_or_same_day(self):
        """测试日期比较"""
        assert DateUtils.is_before_or_same_day("20240101", "20240115") is True
        assert DateUtils.is_before_or_same_day("20240115", "20240115") is True
        assert DateUtils.is_before_or_same_day("20240120", "20240115") is False
