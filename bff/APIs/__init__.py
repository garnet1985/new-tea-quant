"""
BFF APIs 模块
按业务拆分不同的API
"""
from .stock_api import StockApi
from .investment_api import InvestmentApi

__all__ = ['StockApi', 'InvestmentApi']

