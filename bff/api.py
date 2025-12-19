"""
BFF API 统一入口

职责：
- 作为前端与后端各业务 API 之间的中间层
- 统一初始化和复用全局 DataManager
- 对外提供股票和投资相关的 HTTP 接口
"""

import sys
import os
from flask import jsonify
from loguru import logger

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from bff.APIs.stock_api import StockApi
from bff.APIs.investment_api import InvestmentApi
from app.data_manager import DataManager


class BFFApi:
    """BFF API 统一入口类"""
    
    def __init__(self):
        """初始化BFF API"""
        # 使用全局 DataManager 单例（内部会管理 DatabaseManager）
        self.data_mgr = DataManager(is_verbose=False)
        
        # 初始化业务API（惰性创建）
        self._stock_api = None
        self._investment_api = None
    
    @property
    def stock_api(self):
        """股票API（延迟初始化）"""
        if self._stock_api is None:
            # 复用全局 DataManager
            self._stock_api = StockApi(data_mgr=self.data_mgr)
        return self._stock_api
    
    @property
    def investment_api(self):
        """投资API（延迟初始化）"""
        if self._investment_api is None:
            # 复用全局 DataManager
            self._investment_api = InvestmentApi()
        return self._investment_api
    
    # ==================== 健康检查 ====================
    
    def health_check(self):
        """健康检查"""
        return jsonify({
            "success": True,
            "message": "BFF API 运行正常",
            "timestamp": "当前时间"
        })
    
    # ==================== 股票相关 API ====================
    
    def get_stock_kline(self, stock_id: str, term: str = 'daily'):
        """获取股票K线数据"""
        return self.stock_api.get_stock_kline(stock_id, term)
    
    def get_stock_scan(self, strategy: str, stock_id: str):
        """获取股票策略扫描结果"""
        return self.stock_api.get_stock_scan(strategy, stock_id)
    
    def get_stock_simulate(self, strategy: str, stock_id: str):
        """获取股票策略模拟结果"""
        return self.stock_api.get_stock_simulate(strategy, stock_id)
    
    # ==================== 投资相关 API ====================
    
    def get_all_closed_trades(self):
        """获取所有已关闭的交易"""
        return self.investment_api.get_all_closed_trades()
    
    def get_open_positions(self):
        """获取当前持仓"""
        return self.investment_api.get_open_positions()
    
    def get_trades_by_stock(self, stock_id: str):
        """按股票获取交易记录"""
        return self.investment_api.get_trades_by_stock(stock_id)
    
    def get_investment_overview(self):
        """获取投资概览"""
        return self.investment_api.get_investment_overview()


