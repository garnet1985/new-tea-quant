"""
Tushare Provider

用于多个 data source（如 latest_trading_date、kline、corporate_finance 等）
"""
from .provider import TushareProvider

__all__ = ['TushareProvider']
