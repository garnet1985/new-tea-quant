"""
date_utils.py 单元测试
"""
from core.infra.utils import Utils
try:
    import pytest
except ImportError:
    pytest = None

from datetime import datetime
class TestDateUtils:
    """DateUtils 测试类"""
    
    def test_today(self):
        """测试获取当前日期字符串"""
        date_str = Utils.date.today()
        assert len(date_str) == 8
        assert date_str.isdigit()
    
    def test_str_to_format(self):
        """测试日期格式转换"""
        result = Utils.date.str_to_format("20240115", Utils.date.FMT_YYYY_MM_DD)
        assert result == "2024-01-15"
    
    def test_normalize_str(self):
        """测试日期标准化"""
        # YYYYMMDD 格式
        assert Utils.date.normalize_str("20240115") == "20240115"
        
        # YYYY-MM-DD 格式
        assert Utils.date.normalize_str("2024-01-15") == "20240115"
        
        # None
        assert Utils.date.normalize_str(None) is None
        assert Utils.date.normalize_str("") is None
    
    def test_sub_days(self):
        """测试获取 N 天前的日期"""
        result = Utils.date.sub_days("20240115", 5)
        assert result == "20240110"
    
    def test_add_days(self):
        """测试获取 N 天后的日期"""
        result = Utils.date.add_days("20240115", 5)
        assert result == "20240120"
    
    def test_diff_days(self):
        """测试计算天数差"""
        days = Utils.date.diff_days("20240101", "20240115")
        assert days == 14
    
    def test_str_to_datetime(self):
        """测试解析 YYYYMMDD"""
        date_obj = Utils.date.str_to_datetime("20240115")
        assert isinstance(date_obj, datetime)
        assert date_obj.year == 2024
        assert date_obj.month == 1
        assert date_obj.day == 15
    
    def test_date_to_quarter(self):
        """测试日期转季度"""
        assert Utils.date.date_to_quarter("20240115") == "2024Q1"
        assert Utils.date.date_to_quarter("20240415") == "2024Q2"
        assert Utils.date.date_to_quarter("20240715") == "2024Q3"
        assert Utils.date.date_to_quarter("20241015") == "2024Q4"
    
    def test_quarter_to_date(self):
        """测试季度转日期"""
        # 季度开始
        assert Utils.date.quarter_to_date("2024Q1", is_start=True) == "20240101"
        assert Utils.date.quarter_to_date("2024Q2", is_start=True) == "20240401"
        
        # 季度结束
        assert Utils.date.quarter_to_date("2024Q1", is_start=False) == "20240331"
        assert Utils.date.quarter_to_date("2024Q2", is_start=False) == "20240630"
    
    def test_get_current_quarter(self):
        """测试获取当前季度"""
        quarter = Utils.date.get_current_quarter("20240115")
        assert quarter == "2024Q1"
    
    def test_get_quarter_start_date(self):
        """测试获取季度开始日期"""
        assert Utils.date.get_quarter_start_date("2024Q1") == "20240101"
    
    def test_get_next_quarter(self):
        """测试获取下一个季度"""
        assert Utils.date.get_next_quarter("2024Q1") == "2024Q2"
        assert Utils.date.get_next_quarter("2024Q4") == "2025Q1"
    
    def test_get_previous_week_end(self):
        """测试获取前一周的周日"""
        # 20250930 是周二，前一周的周日应该是 20250928
        result = Utils.date.get_previous_week_end("20250930")
        assert result == "20250928"
    
    def test_get_previous_month_end(self):
        """测试获取前一个月的最后一天"""
        assert Utils.date.get_previous_month_end("20250930") == "20250831"
        assert Utils.date.get_previous_month_end("20250115") == "20241231"
    
    def test_is_before(self):
        """测试日期比较"""
        assert Utils.date.is_before("20240101", "20240115") is True
        assert Utils.date.is_before("20240115", "20240115") is False
        assert Utils.date.is_before("20240120", "20240115") is False
    
    def test_is_same(self):
        """测试是否同一天"""
        assert Utils.date.is_same("20240115", "20240115") is True
        assert Utils.date.is_same("20240115", "20240116") is False
    
    def test_to_period_str(self):
        """测试日期转周期字符串"""
        assert Utils.date.to_period_str("20240115", Utils.date.PERIOD_DAY) == "20240115"
        assert Utils.date.to_period_str("20240115", Utils.date.PERIOD_MONTH) == "202401"
        assert Utils.date.to_period_str("20240115", Utils.date.PERIOD_QUARTER) == "2024Q1"
    
    def test_from_period_str(self):
        """测试周期字符串转日期"""
        assert Utils.date.from_period_str("202401", Utils.date.PERIOD_MONTH, is_start=True) == "20240101"
        assert Utils.date.from_period_str("2024Q1", Utils.date.PERIOD_QUARTER, is_start=True) == "20240101"
    
    def test_add_periods(self):
        """测试周期加法"""
        assert Utils.date.add_periods("202401", 3, Utils.date.PERIOD_MONTH) == "202404"
        assert Utils.date.add_periods("2024Q1", 2, Utils.date.PERIOD_QUARTER) == "2024Q3"
    
    def test_sub_periods(self):
        """测试周期减法"""
        assert Utils.date.sub_periods("202404", 3, Utils.date.PERIOD_MONTH) == "202401"
        assert Utils.date.sub_periods("2024Q3", 2, Utils.date.PERIOD_QUARTER) == "2024Q1"
    
    def test_diff_periods(self):
        """测试周期差值"""
        assert Utils.date.diff_periods("202401", "202404", Utils.date.PERIOD_MONTH) == 3
        assert Utils.date.diff_periods("2024Q1", "2024Q3", Utils.date.PERIOD_QUARTER) == 2
    
    def test_normalize_period_value(self):
        """测试周期值标准化"""
        assert Utils.date.normalize_period_value("2024-01-15", Utils.date.PERIOD_MONTH) == "202401"
        assert Utils.date.normalize_period_value("2024-01-15", Utils.date.PERIOD_QUARTER) == "2024Q1"
        assert Utils.date.normalize_period_value(datetime(2024, 1, 15), Utils.date.PERIOD_MONTH) == "202401"
