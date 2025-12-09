"""
日线数据 Handler

从 Tushare 获取股票日线数据（包含 K 线和基本面指标）
"""
from app.data_source.defaults.handlers.base_kline_handler import BaseKlineHandler


class DailyKlineHandler(BaseKlineHandler):
    """
    日线数据 Handler
    """
    data_source = "daily_kline"
    renew_type = "incremental"
    description = "获取日线数据（包含 K 线和基本面指标）"
    dependencies = ["stock_list"]
    requires_date_range = True
    
    term = "daily"
    kline_method = "get_daily_kline"

