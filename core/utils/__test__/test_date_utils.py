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
    
    def test_today(self):
        """测试获取当前日期字符串"""
        date_str = DateUtils.today()
        assert len(date_str) == 8
        assert date_str.isdigit()
    
    def test_str_to_format(self):
        """测试日期格式转换"""
        result = DateUtils.str_to_format("20240115", DateUtils.FMT_YYYY_MM_DD)
        assert result == "2024-01-15"
    
    def test_normalize_str(self):
        """测试日期标准化"""
        # YYYYMMDD 格式
        assert DateUtils.normalize_str("20240115") == "20240115"
        
        # YYYY-MM-DD 格式
        assert DateUtils.normalize_str("2024-01-15") == "20240115"
        
        # None
        assert DateUtils.normalize_str(None) is None
        assert DateUtils.normalize_str("") is None
    
    def test_sub_days(self):
        """测试获取 N 天前的日期"""
        result = DateUtils.sub_days("20240115", 5)
        assert result == "20240110"
    
    def test_add_days(self):
        """测试获取 N 天后的日期"""
        result = DateUtils.add_days("20240115", 5)
        assert result == "20240120"
    
    def test_diff_days(self):
        """测试计算天数差"""
        days = DateUtils.diff_days("20240101", "20240115")
        assert days == 14
    
    def test_str_to_datetime(self):
        """测试解析 YYYYMMDD"""
        date_obj = DateUtils.str_to_datetime("20240115")
        assert isinstance(date_obj, datetime)
        assert date_obj.year == 2024
        assert date_obj.month == 1
        assert date_obj.day == 15
    
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
    
    def test_get_quarter_start_date(self):
        """测试获取季度开始日期"""
        assert DateUtils.get_quarter_start_date("2024Q1") == "20240101"
    
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
    
    def test_is_before(self):
        """测试日期比较"""
        assert DateUtils.is_before("20240101", "20240115") is True
        assert DateUtils.is_before("20240115", "20240115") is False
        assert DateUtils.is_before("20240120", "20240115") is False
    
    def test_is_same(self):
        """测试是否同一天"""
        assert DateUtils.is_same("20240115", "20240115") is True
        assert DateUtils.is_same("20240115", "20240116") is False
    
    def test_to_period_str(self):
        """测试日期转周期字符串"""
        assert DateUtils.to_period_str("20240115", DateUtils.PERIOD_DAY) == "20240115"
        assert DateUtils.to_period_str("20240115", DateUtils.PERIOD_MONTH) == "202401"
        assert DateUtils.to_period_str("20240115", DateUtils.PERIOD_QUARTER) == "2024Q1"
    
    def test_from_period_str(self):
        """测试周期字符串转日期"""
        assert DateUtils.from_period_str("202401", DateUtils.PERIOD_MONTH, is_start=True) == "20240101"
        assert DateUtils.from_period_str("2024Q1", DateUtils.PERIOD_QUARTER, is_start=True) == "20240101"
    
    def test_add_periods(self):
        """测试周期加法"""
        assert DateUtils.add_periods("202401", 3, DateUtils.PERIOD_MONTH) == "202404"
        assert DateUtils.add_periods("2024Q1", 2, DateUtils.PERIOD_QUARTER) == "2024Q3"
    
    def test_sub_periods(self):
        """测试周期减法"""
        assert DateUtils.sub_periods("202404", 3, DateUtils.PERIOD_MONTH) == "202401"
        assert DateUtils.sub_periods("2024Q3", 2, DateUtils.PERIOD_QUARTER) == "2024Q1"
    
    def test_diff_periods(self):
        """测试周期差值"""
        assert DateUtils.diff_periods("202401", "202404", DateUtils.PERIOD_MONTH) == 3
        assert DateUtils.diff_periods("2024Q1", "2024Q3", DateUtils.PERIOD_QUARTER) == 2
    
    def test_normalize_period_value(self):
        """测试周期值标准化"""
        assert DateUtils.normalize_period_value("2024-01-15", DateUtils.PERIOD_MONTH) == "202401"
        assert DateUtils.normalize_period_value("2024-01-15", DateUtils.PERIOD_QUARTER) == "2024Q1"
        assert DateUtils.normalize_period_value(datetime(2024, 1, 15), DateUtils.PERIOD_MONTH) == "202401"
